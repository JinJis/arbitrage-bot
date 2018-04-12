import time
import logging
import numpy as np
from config.global_conf import Global
from analyzer.analyzer import Analyzer
from trader.market.market import Market
from trader.base_arb_bot import BaseArbBot
from config.shared_mongo_client import SharedMongoClient
from trader.market.trade import Trade, TradeTag, StatArbTradeMeta
from trader.trade_manager.order_watcher_stats import OrderWatcherStats
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator


class StatArbBot(BaseArbBot):
    TARGET_SPREAD_FUNCTION = Analyzer.get_orderbook_mid_price_log_spread

    def __init__(self,
                 target_currency: str = "eth", target_interval_in_sec: int = 5,
                 should_db_logging: bool = True,
                 is_backtesting: bool = False, start_time: int = None, end_time: int = None):

        # init virtual mm when backtesting
        v_mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 45000, 0.11) if is_backtesting else None
        v_mm2 = VirtualMarketManager(Market.VIRTUAL_KB, 0.0008, 45000, 0.11) if is_backtesting else None

        super().__init__(target_currency, target_interval_in_sec,
                         should_db_logging, is_backtesting, start_time, end_time, v_mm1, v_mm2)

        self.COIN_TRADING_UNIT = 0.1
        self.TARGET_SPREAD_STACK_HOUR = 18
        self.TARGET_SPREAD_STACK_SIZE = (60 / self.TRADE_INTERVAL_IN_SEC) * 60 * self.TARGET_SPREAD_STACK_HOUR
        self.Z_SCORE_SIGMA = Global.get_z_score_for_probability(0.9)
        self.TARGET_DATA_COL = "orderbook"

        # init mongo related
        self.mm1_data_col = SharedMongoClient.get_coinone_db()[self.TARGET_CURRENCY + "_" + self.TARGET_DATA_COL]
        self.mm2_data_col = SharedMongoClient.get_korbit_db()[self.TARGET_CURRENCY + "_" + self.TARGET_DATA_COL]

        # init spread stack
        self.spread_stack = np.array([], dtype=np.float32)

    def run(self):
        #################################
        # LOG INITIAL BALANCE
        #################################

        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(self.mm1.get_balance())
        logging.info(self.mm2.get_balance())

        #################################
        # COLLECT INITIAL SPREAD STACK
        #################################

        logging.info("Collecting initial spread stack, please wait...")
        if not self.is_backtesting:
            last_request_time = self.collect_initial_stack(int(time.time()))
        else:
            last_request_time = self.collect_initial_stack(self.start_time)
        logging.warning("Done collecting! Stack size - expected: %d, current: %d" %
                        (self.TARGET_SPREAD_STACK_SIZE, self.spread_stack.size))

        #################################
        # EXECUTE TRADE LOOP
        #################################

        # on actual execution
        if not self.is_backtesting:

            # calculate and wait for request time gap to match the trade interval
            current_ts = time.time()
            wait_n_sec = self.TRADE_INTERVAL_IN_SEC - (current_ts - last_request_time)
            logging.info("Last requestTime: %.2f, current: %.2f, will wait %.2f sec..." %
                         (last_request_time, current_ts, wait_n_sec))
            if wait_n_sec > 0:
                time.sleep(wait_n_sec)

            # jump into start loop
            while True:
                try:
                    self.execute_trade_loop()
                except Exception as e:
                    Global.send_to_slack_channel("Something happened to StatArbBot! Now it's dying from ... %s" % e)
                    # stop order watcher stats thread
                    OrderWatcherStats.instance().tear_down()
                    raise e

        # on backtesting
        else:
            # collect historical data from db
            logging.info("Collecting historical data, please wait...")
            mm1_data_cursor, mm2_data_cursor = \
                self.get_data_from_db(self.start_time, self.end_time)

            # loop through history data
            for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
                self.execute_trade_loop(mm1_data, mm2_data)

            # log backtesting result
            self.log_common_stat(log_level=logging.CRITICAL)

    def actual_trade_loop(self, mm1_data=None, mm2_data=None):
        # get previous mean, standard deviation
        mean = self.spread_stack.mean()
        stdev = self.spread_stack.std()

        # get upper & lower bound
        upper = mean + stdev * self.Z_SCORE_SIGMA
        lower = mean - stdev * self.Z_SCORE_SIGMA

        # get current spread
        if not self.is_backtesting:
            mm1_data = self.mm1.get_orderbook(self.mm1_currency)
            mm2_data = self.mm2.get_orderbook(self.mm2_currency)
            cur_spread, mm1_price, mm2_price = StatArbBot.TARGET_SPREAD_FUNCTION(mm1_data, mm2_data)
        else:
            # on backtesting
            cur_spread, mm1_price, mm2_price = StatArbBot.TARGET_SPREAD_FUNCTION(mm1_data, mm2_data)

        # calculate plain spread
        plain_spread = mm1_price - mm2_price

        # log stat
        logging.info("[STAT] cur_spread: %.8f, mean: %.8f, stdev: %.8f" % (cur_spread, mean, stdev))
        logging.info("[STAT] mm1_price: %d, mm2_price: %d, plain_spread: %d" % (mm1_price, mm2_price, plain_spread))
        trade_meta = StatArbTradeMeta(plain_spread, cur_spread, mean, stdev, upper, lower)

        # make decision
        if cur_spread < lower:
            # NEW: long in mm1, short in mm2
            self.new_oppty_counter += 1
            fee, should_fee = Analyzer.get_fee_consideration(self.mm1.get_market_tag(), self.TARGET_CURRENCY)
            trading_unit = self.COIN_TRADING_UNIT + fee if should_fee else self.COIN_TRADING_UNIT

            # check balance
            if Analyzer.have_enough_balance_for_arb(self.mm1, self.mm2, mm1_price,
                                                    trading_unit, self.TARGET_CURRENCY):
                logging.warning("[EXECUTE] New")
                buy_order = self.mm1.order_buy(self.mm1_currency, mm1_price, trading_unit)
                sell_order = self.mm2.order_sell(self.mm2_currency, mm2_price, trading_unit)
                self.cur_trade = Trade(TradeTag.NEW, [buy_order, sell_order], trade_meta)

                # subtract considered fee if there was one
                if should_fee:
                    GlobalFeeAccumulator.sub_fee_consideration(self.mm1.get_market_tag(), self.TARGET_CURRENCY, fee)
            else:
                logging.error("[EXECUTE] New -> failed (not enough balance!)")

        elif cur_spread > upper:
            # REV: long in mm2, short in mm1
            self.rev_oppty_counter += 1
            fee, should_fee = Analyzer.get_fee_consideration(self.mm2.get_market_tag(), self.TARGET_CURRENCY)
            trading_unit = self.COIN_TRADING_UNIT + fee if should_fee else self.COIN_TRADING_UNIT

            # check balance
            if Analyzer.have_enough_balance_for_arb(self.mm2, self.mm1, mm2_price,
                                                    trading_unit, self.TARGET_CURRENCY):
                logging.warning("[EXECUTE] Reverse")
                buy_order = self.mm2.order_buy(self.mm2_currency, mm2_price, trading_unit)
                sell_order = self.mm1.order_sell(self.mm1_currency, mm1_price, trading_unit)
                self.cur_trade = Trade(TradeTag.REV, [buy_order, sell_order], trade_meta)

                # subtract considered fee if there was one
                if should_fee:
                    GlobalFeeAccumulator.sub_fee_consideration(self.mm2.get_market_tag(), self.TARGET_CURRENCY, fee)
            else:
                logging.error("[EXECUTE] Reverse -> failed (not enough balance!)")

        else:
            logging.warning("[EXECUTE] No")

        # if any trade was executed
        if self.cur_trade is not None:
            # change timestamp of trade when backtesting
            if self.is_backtesting:
                current_ts = mm1_data["requestTime"]
                self.cur_trade.set_timestamp(current_ts)

            # add into trade list
            self.trade_manager.add_trade(self.cur_trade)

            # update balance
            self.mm1.update_balance()
            self.mm2.update_balance()

        # log stat if it's not back testing
        if not self.is_backtesting:
            self.log_common_stat()
            # db log balance
            timestamp = int(time.time())
            self.mm1.db_log_balance(timestamp)
            self.mm2.db_log_balance(timestamp)

        # remove the earliest spread in the stack
        # append the current spread
        self.spread_stack = np.delete(self.spread_stack, 0)
        self.spread_stack = np.append(self.spread_stack, cur_spread)

    def collect_initial_stack(self, current_timestamp: int):
        target_timestamp = current_timestamp - 60 * 60 * self.TARGET_SPREAD_STACK_HOUR
        mm1_cursor, mm2_cursor = self.get_data_from_db(target_timestamp, current_timestamp)

        last_request_time = None
        for mm1_data, mm2_data in zip(mm1_cursor, mm2_cursor):
            log_spread, _, _ = StatArbBot.TARGET_SPREAD_FUNCTION(mm1_data, mm2_data)
            self.spread_stack = np.append(self.spread_stack, log_spread)
            last_request_time = mm1_data["requestTime"]

        # return the last request time
        return last_request_time

    def get_data_from_db(self, start_time: int, end_time: int):
        mm1_cursor = self.mm1_data_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])
        mm2_cursor = self.mm2_data_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        mm1_count = mm1_cursor.count()
        mm2_count = mm2_cursor.count()
        if mm1_count != mm2_count:
            logging.warning("Cursor count does not match! : mm1 %d, mm2 %d" % (mm1_count, mm2_count))
            logging.info("Now validating data...")
            Global.request_time_validation_on_cursor_count_diff(mm1_cursor, mm2_cursor)

        return mm1_cursor, mm2_cursor
