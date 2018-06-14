import time
import logging
from abc import ABC, abstractmethod
from config.global_conf import Global
from analyzer.analyzer import BasicAnalyzer
from trader.market.trade import TradeTag
from pymongo.collection import Collection
from trader.trade_manager.trade_manager import TradeManager
from trader.trade_manager.order_watcher_stats import OrderWatcherStats
from trader.market_manager.market_manager import MarketManager


class BaseArbBot(ABC):
    DELAYED_ORDER_COUNT_THRESHOLD = 10

    def __init__(self,
                 mm1: MarketManager, mm2: MarketManager,
                 target_currency: str, target_interval_in_sec: int = 5,
                 should_db_logging: bool = True,
                 is_backtesting: bool = False,
                 start_time: int = None, end_time: int = None):

        self.TARGET_CURRENCY = target_currency
        self.TRADE_INTERVAL_IN_SEC = target_interval_in_sec

        self.should_db_logging = should_db_logging
        self.is_backtesting = is_backtesting
        self.start_time = start_time
        self.end_time = end_time

        # init market managers
        self.mm1 = mm1
        self.mm2 = mm2

        if not self.is_backtesting:
            # initialize global OrderWatcherStats
            # will initiate a thread for OrderWatcherStats
            OrderWatcherStats.initialize()

        # set market currency
        self.mm1_currency = self.mm1.get_market_currency(self.TARGET_CURRENCY)
        self.mm2_currency = self.mm2.get_market_currency(self.TARGET_CURRENCY)

        self.trade_manager = TradeManager(should_db_logging=should_db_logging, is_backtesting=is_backtesting)
        self.loop_count = 0
        self.loop_start_time = None
        self.loop_end_time = None
        self.new_oppty_counter = 0
        self.rev_oppty_counter = 0
        self.cur_trade = None
        self.total_krw_bal = 0

    def trade_loop_start(self):
        # print trade loop seq
        self.loop_count += 1
        logging.info("========== [# %12d Trade Loop] =================================================="
                     % self.loop_count)
        self.loop_start_time = time.time()

    def trade_loop_end(self):
        # sleep for diff between the set interval and execution time
        self.loop_end_time = time.time()
        loop_spent_time = self.loop_end_time - self.loop_start_time
        sleep_time = self.TRADE_INTERVAL_IN_SEC - loop_spent_time
        if sleep_time > 0:
            time.sleep(sleep_time)

    def execute_trade_loop(self, mm1_data=None, mm2_data=None):
        if not self.is_backtesting:
            self.trade_loop_start()
        # refresh cur_trade
        self.cur_trade = None
        self.actual_trade_loop(mm1_data, mm2_data)
        if not self.is_backtesting:
            self.trade_loop_end()

    @abstractmethod
    def actual_trade_loop(self, mm1_data=None, mm2_data=None):
        pass

    @abstractmethod
    def run(self):
        pass

    def log_common_stat(self, log_level: int = logging.INFO):
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
        logging.log(log_level, "[STAT] switch over - count: %d, average: %.2f sec, last: %.2f sec \n" %
                    (self.trade_manager.get_switch_over_count(),
                     self.trade_manager.get_average_switch_over_spent_time(),
                     last_switch_over.get("spent_time") if last_switch_over is not None else 0))

        # log balance
        mm1_balance = self.mm1.get_balance()
        mm2_balance = self.mm2.get_balance()
        logging.log(log_level, mm1_balance)
        logging.log(log_level, mm2_balance)

        # log combined balance
        combined = BasicAnalyzer.combine_balance(mm1_balance, mm2_balance, (self.TARGET_CURRENCY, "krw"))
        for coin_name in combined.keys():
            balance = combined[coin_name]
            logging.log(log_level, "\n[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                        (coin_name, balance["available"], balance["trade_in_use"], balance["balance"]))

    def get_krw_total_balance(self):
        # log balance
        mm1_balance = self.mm1.get_balance()
        mm2_balance = self.mm2.get_balance()

        # log combined balance
        combined = BasicAnalyzer.combine_balance(mm1_balance, mm2_balance, (self.TARGET_CURRENCY, "krw"))
        return combined["KRW"]["balance"]

    def log_order_watcher_stats(self):
        ows_stats = OrderWatcherStats.instance().get_stats()
        logging.info("[STAT] order watcher - %s" % ows_stats)
        delayed_count = ows_stats.get("active_delayed_count")
        if delayed_count > self.DELAYED_ORDER_COUNT_THRESHOLD:
            logging.warning("[Warning] delayed orders: %s" % OrderWatcherStats.instance().get_current_delayed())

    @staticmethod
    def get_data_from_db(mm1_data_col: Collection, mm2_data_col: Collection, start_time: int, end_time: int):
        mm1_cursor = mm1_data_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])
        mm2_cursor = mm2_data_col.find({"requestTime": {
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

    def clear_oppty_counter(self):
        self.new_oppty_counter = 0
        self.rev_oppty_counter = 0
