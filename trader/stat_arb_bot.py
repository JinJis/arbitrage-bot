import math
import time
import logging
import numpy as np
from pymongo import MongoClient
from analyzer.analyzer import Analyzer
from config.global_conf import Global
from trader.market.trade import ArbTrade, TradeTag, StatArbTradeMeta
from trader.trade_manager import TradeManager
from trader.market_manager.market_manager import MarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.virtual_market_manager import VirtualMarketManager, VirtualMarketApiType


class StatArbBot:
    TARGET_CURRENCY = "eth"
    COIN_TRADING_UNIT = 0.01
    TRADE_INTERVAL_IN_SEC = 5
    TARGET_SPREAD_STACK_HOUR = 3  # 3-hour data
    TARGET_SPREAD_STACK_SIZE = (60 / TRADE_INTERVAL_IN_SEC) * 60 * TARGET_SPREAD_STACK_HOUR
    Z_SCORE_SIGMA = Global.get_z_score_for_probability(0.8)  # 2

    def __init__(self, is_from_local: bool = False):
        # init market managers
        # self.coinone_mm = CoinoneMarketManager()
        # self.korbit_mm = KorbitMarketManager()
        self.v_coinone_mm = VirtualMarketManager("co", VirtualMarketApiType.COINONE, 0.001, 60000, 0.1)
        self.v_korbit_mm = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT, 0.0008, 60000, 0.1)

        # init spread stack
        self.spread_stack = np.array([], dtype=np.float32)

        # init mongo client
        self.mongo_client = MongoClient(Global.read_mongodb_uri(is_from_local))
        self.co_ticker_col = self.mongo_client["coinone"][self.TARGET_CURRENCY + "_ticker"]
        self.kb_ticker_col = self.mongo_client["korbit"][self.TARGET_CURRENCY + "_ticker"]

        # init trade manager
        self.trade_manager = TradeManager()

    def run(self):
        Global.configure_default_root_logging()
        self.execute(self.v_coinone_mm, self.v_korbit_mm)

    def execute(self, mm1: MarketManager, mm2: MarketManager):
        # get currency for each market
        mm1_currency = mm1.get_market_currency(self.TARGET_CURRENCY)
        mm2_currency = mm2.get_market_currency(self.TARGET_CURRENCY)

        # collect initial stack before going into trade loop
        logging.info("Collecting initial spread stack, please wait...")
        last_request_time = self.collect_initial_stack()
        logging.warning("Done collecting! Stack size - expected: %d, current: %d" %
                        (self.TARGET_SPREAD_STACK_SIZE, self.spread_stack.size))

        # calculate and wait for request time gap to match the trade interval
        current_ts = time.time()
        wait_n_sec = self.TRADE_INTERVAL_IN_SEC - (current_ts - last_request_time)
        logging.info("Last requestTime: %.2f, current: %.2f, will wait %.2f sec..." %
                     (last_request_time, current_ts, wait_n_sec))
        time.sleep(wait_n_sec if wait_n_sec > 0 else 0)

        # log initial balance
        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(mm1.get_balance())
        logging.info(mm2.get_balance())

        # init loop count
        loop_count = 1

        while True:
            # print trade loop seq
            logging.info("========== [# %12d Trade Loop] =================================================="
                         % loop_count)
            loop_count += 1
            loop_start_time = time.time()
            trade = None

            # get previous mean, standard deviation
            mean = self.spread_stack.mean()
            stdev = self.spread_stack.std()

            # get upper & lower bound
            upper = mean + stdev * StatArbBot.Z_SCORE_SIGMA
            lower = mean - stdev * StatArbBot.Z_SCORE_SIGMA

            # get current spread
            cur_spread, mm1_last, mm2_last = Analyzer.get_ticker_log_spread(mm1, mm1_currency, mm2, mm2_currency)
            plain_spread = mm1_last - mm2_last

            # log stat
            logging.info("[STAT] cur_spread: %.8f, mean: %.8f, stdev: %.8f" % (cur_spread, mean, stdev))
            logging.info("[STAT] mm1_last: %d, mm2_last: %d, plain_spread: %d" % (mm1_last, mm2_last, plain_spread))
            trade_meta = StatArbTradeMeta(plain_spread, cur_spread, mean, stdev, upper, lower)

            # make decision
            if cur_spread < lower:
                # check balance
                if (mm1.has_enough_coin("krw", mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm1_last)
                        and mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)):
                    logging.warning("[EXECUTE] New")
                    # long in mm1, short in mm2
                    buy_order = mm1.order_buy(mm1_currency, mm1_last, self.COIN_TRADING_UNIT)
                    sell_order = mm2.order_sell(mm2_currency, mm2_last, self.COIN_TRADING_UNIT)
                    trade = ArbTrade(TradeTag.NEW, [buy_order, sell_order], trade_meta)
                else:
                    logging.error("[EXECUTE] New -> failed (not enough balance!)")

            elif cur_spread > upper:
                # check balance
                if (mm2.has_enough_coin("krw", mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm2_last)
                        and mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)):
                    logging.warning("[EXECUTE] Reverse")
                    # long in mm2, short in mm1
                    buy_order = mm2.order_buy(mm2_currency, mm2_last, self.COIN_TRADING_UNIT)
                    sell_order = mm1.order_sell(mm1_currency, mm1_last, self.COIN_TRADING_UNIT)
                    trade = ArbTrade(TradeTag.REV, [buy_order, sell_order], trade_meta)
                else:
                    logging.error("[EXECUTE] Reverse -> failed (not enough balance!)")

            else:
                logging.warning("[EXECUTE] No")

            # TODO: log trade, keep track of trades in trade manager
            # if any trade was executed
            if trade is not None:
                # add into trade list
                self.trade_manager.add_trade(trade)

                # update and log balance
                mm1.update_balance()
                mm2.update_balance()
                logging.info(mm1.get_balance())
                logging.info(mm2.get_balance())

            # log trade stat
            trade_total = self.trade_manager.get_trade_count()
            trade_new = self.trade_manager.get_trade_count(TradeTag.NEW)
            trade_rev = self.trade_manager.get_trade_count(TradeTag.REV)
            try:
                logging.info("[STAT] total trades: %d, new trades: %d(%.2f%%), rev trades: %d(%.2f%%)" %
                             (trade_total, trade_new, trade_new / trade_total * 100,
                              trade_rev, trade_rev / trade_total * 100))
            except ZeroDivisionError:
                logging.info("[STAT] total trades: 0, new trades: 0, rev trades: 0")

            # log switch over stat
            last_switch_over = self.trade_manager.get_last_switch_over()
            logging.info("[STAT] switch over - count: %d, average: %.2f sec, last: %.2f sec" %
                         (self.trade_manager.get_switch_over_count(),
                          self.trade_manager.get_average_switch_over_spent_time(),
                          last_switch_over.get("spent_time") if last_switch_over is not None else 0))

            # log combined balance
            Analyzer.log_combined_balance(mm1.get_balance(), mm2.get_balance())

            # remove the earliest spread in the stack
            # append the current spread
            self.spread_stack = np.delete(self.spread_stack, 0)
            self.spread_stack = np.append(self.spread_stack, cur_spread)

            # sleep for diff between the set interval and execution time
            loop_end_time = time.time()
            loop_spent_time = loop_end_time - loop_start_time
            time.sleep(self.TRADE_INTERVAL_IN_SEC - loop_spent_time)

    def collect_initial_stack(self):
        current_timestamp = int(time.time())
        target_timestamp = current_timestamp - 60 * 60 * self.TARGET_SPREAD_STACK_HOUR

        co_cursor = self.co_ticker_col.find({"requestTime": {
            "$gte": target_timestamp,
            "$lte": current_timestamp
        }}).sort([("requestTime", 1)])
        kb_cursor = self.kb_ticker_col.find({"requestTime": {
            "$gte": target_timestamp,
            "$lte": current_timestamp
        }}).sort([("requestTime", 1)])

        co_count = co_cursor.count()
        kb_count = kb_cursor.count()
        if co_count != kb_count:
            raise Exception("[Initialization Error] Cursor count does not match! : co %d, kb %d" % (co_count, kb_count))

        last_request_time = None
        for co_item, kb_item in zip(co_cursor, kb_cursor):
            co_last = co_item["last"].to_decimal()
            kb_last = kb_item["last"].to_decimal()
            log_spread = math.log(co_last) - math.log(kb_last)
            self.spread_stack = np.append(self.spread_stack, log_spread)
            last_request_time = co_item["requestTime"]

        # return the last request time
        return last_request_time
