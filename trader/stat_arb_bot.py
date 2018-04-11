import time
import logging
import numpy as np
from analyzer.analyzer import Analyzer
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.market.trade import Trade, TradeTag, StatArbTradeMeta
from trader.trade_manager.trade_manager import TradeManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.virtual_market_manager import VirtualMarketManager, VirtualMarketApiType
from trader.trade_manager.order_watcher_stats import OrderWatcherStats


class StatArbBot:
    TARGET_CURRENCY = "eth"
    COIN_TRADING_UNIT = 0.01
    TRADE_INTERVAL_IN_SEC = 5
    TARGET_SPREAD_STACK_HOUR = 12
    TARGET_SPREAD_STACK_SIZE = (60 / TRADE_INTERVAL_IN_SEC) * 60 * TARGET_SPREAD_STACK_HOUR
    Z_SCORE_SIGMA = Global.get_z_score_for_probability(0.9)
    DELAYED_ORDER_COUNT_THRESHOLD = 10
    TARGET_SPREAD_FUNCTION = Analyzer.get_orderbook_mid_price_log_spread
    TARGET_DATA_COL = "orderbook"

    def __init__(self, should_db_logging: bool = True,
                 is_backtesting: bool = False, start_time: int = None, end_time: int = None):
        # for backtesting
        self.is_backtesting = is_backtesting
        self.start_time = start_time
        self.end_time = end_time

        # init market managers
        if not self.is_backtesting:
            self.mm1 = CoinoneMarketManager()
            self.mm2 = KorbitMarketManager()
            # initialize global OrderWatcherStats
            # will initiate a thread for OrderWatcherStats
            OrderWatcherStats.initialize()
        else:
            self.mm1 = VirtualMarketManager("co", VirtualMarketApiType.COINONE, 0.001, 60000, 0.1)
            self.mm2 = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT, 0.002, 60000, 0.1)

        # set market currency
        self.mm1_currency = self.mm1.get_market_currency(self.TARGET_CURRENCY)
        self.mm2_currency = self.mm2.get_market_currency(self.TARGET_CURRENCY)

        # init mongo related
        self.mm1_data_col = SharedMongoClient.get_coinone_db()[self.TARGET_CURRENCY + "_" + self.TARGET_DATA_COL]
        self.mm2_data_col = SharedMongoClient.get_korbit_db()[self.TARGET_CURRENCY + "_" + self.TARGET_DATA_COL]

        # init other attributes
        self.spread_stack = np.array([], dtype=np.float32)
        self.trade_manager = TradeManager(should_db_logging=should_db_logging, is_backtesting=is_backtesting)
        self.loop_count = 0
        self.new_oppty_counter = 0
        self.rev_oppty_counter = 0

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

    def execute_trade_loop(self, mm1_data=None, mm2_data=None):
        # print trade loop seq
        self.loop_count += 1
        logging.info("========== [# %12d Trade Loop] =================================================="
                     % self.loop_count)
        loop_start_time = time.time()
        trade = None

        # get previous mean, standard deviation
        mean = self.spread_stack.mean()
        stdev = self.spread_stack.std()

        # get upper & lower bound
        upper = mean + stdev * StatArbBot.Z_SCORE_SIGMA
        lower = mean - stdev * StatArbBot.Z_SCORE_SIGMA

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
            self.new_oppty_counter += 1
            # check balance
            if Analyzer.have_enough_balance_for_arb(self.mm1, self.mm2, mm1_price,
                                                    self.COIN_TRADING_UNIT, self.TARGET_CURRENCY):
                # long in mm1, short in mm2
                logging.warning("[EXECUTE] New")
                buy_order = self.mm1.order_buy(self.mm1_currency, mm1_price, self.COIN_TRADING_UNIT)
                sell_order = self.mm2.order_sell(self.mm2_currency, mm2_price, self.COIN_TRADING_UNIT)
                trade = Trade(TradeTag.NEW, [buy_order, sell_order], trade_meta)
            else:
                logging.error("[EXECUTE] New -> failed (not enough balance!)")

        elif cur_spread > upper:
            self.rev_oppty_counter += 1
            # check balance
            if Analyzer.have_enough_balance_for_arb(self.mm2, self.mm1, mm2_price,
                                                    self.COIN_TRADING_UNIT, self.TARGET_CURRENCY):
                # long in mm2, short in mm1
                logging.warning("[EXECUTE] Reverse")
                buy_order = self.mm2.order_buy(self.mm2_currency, mm2_price, self.COIN_TRADING_UNIT)
                sell_order = self.mm1.order_sell(self.mm1_currency, mm1_price, self.COIN_TRADING_UNIT)
                trade = Trade(TradeTag.REV, [buy_order, sell_order], trade_meta)
            else:
                logging.error("[EXECUTE] Reverse -> failed (not enough balance!)")

        else:
            logging.warning("[EXECUTE] No")

        # if any trade was executed
        if trade is not None:
            # change timestamp of trade when backtesting
            if self.is_backtesting:
                current_ts = mm1_data["requestTime"]
                trade.set_timestamp(current_ts)

            # add into trade list
            self.trade_manager.add_trade(trade)

            # update balance
            self.mm1.update_balance()
            self.mm2.update_balance()

        # log stat if it's not back testing
        if not self.is_backtesting:
            self.log_common_stat()

            # log order watcher stats
            ows_stats = OrderWatcherStats.instance().get_stats()
            logging.info("[STAT] order watcher - %s" % ows_stats)
            delayed_count = ows_stats.get("active_delayed_count")
            if delayed_count > self.DELAYED_ORDER_COUNT_THRESHOLD:
                logging.warning("[Warning] delayed orders: %s" % OrderWatcherStats.instance().get_current_delayed())

        # remove the earliest spread in the stack
        # append the current spread
        self.spread_stack = np.delete(self.spread_stack, 0)
        self.spread_stack = np.append(self.spread_stack, cur_spread)

        # sleep for diff between the set interval and execution time
        loop_end_time = time.time()
        loop_spent_time = loop_end_time - loop_start_time
        sleep_time = self.TRADE_INTERVAL_IN_SEC - loop_spent_time
        if sleep_time > 0 and not self.is_backtesting:
            time.sleep(sleep_time)

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

    # extracted for backtesting result logging
    def log_common_stat(self, log_level: int = logging.INFO):
        # log balance
        self.trade_manager.log_balance(self.mm1.get_balance())
        self.trade_manager.log_balance(self.mm2.get_balance())

        # log trade stat
        trade_total = self.trade_manager.get_trade_count()
        trade_new = self.trade_manager.get_trade_count(TradeTag.NEW)
        trade_rev = self.trade_manager.get_trade_count(TradeTag.REV)
        try:
            logging.log(log_level, "[STAT] total trades: %d, new trades: %d(%.2f%%), rev trades: %d(%.2f%%)" %
                        (trade_total, trade_new, trade_new / trade_total * 100,
                         trade_rev, trade_rev / trade_total * 100))
        except ZeroDivisionError:
            logging.log(log_level, "[STAT] total trades: 0, new trades: 0, rev trades: 0")

        # log opportunity counter
        logging.log(log_level, "[STAT] total oppty: %d, new oppty: %d, rev oppty: %d" %
                    (self.new_oppty_counter + self.rev_oppty_counter,
                     self.new_oppty_counter, self.rev_oppty_counter))

        # log switch over stat
        last_switch_over = self.trade_manager.get_last_switch_over()
        logging.log(log_level, "[STAT] switch over - count: %d, average: %.2f sec, last: %.2f sec" %
                    (self.trade_manager.get_switch_over_count(),
                     self.trade_manager.get_average_switch_over_spent_time(),
                     last_switch_over.get("spent_time") if last_switch_over is not None else 0))

        # log combined balance
        combined = Analyzer.combine_balance(self.mm1.get_balance(), self.mm2.get_balance())
        for coin_name in combined.keys():
            balance = combined[coin_name]
            logging.log(log_level, "[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                        (coin_name, balance["available"], balance["trade_in_use"], balance["balance"]))
