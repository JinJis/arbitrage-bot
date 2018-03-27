import time
import logging
import numpy as np
from trader.market_manager.market_manager import MarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.virtual_market_manager import VirtualMarketManager, VirtualMarketApiType
from config.global_conf import Global
from analyzer.analyzer import Analyzer
from pymongo import MongoClient
import math


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

    def run(self):
        Global.configure_default_root_logging()
        self.execute(self.v_coinone_mm, self.v_korbit_mm)

    def execute(self, mm1: MarketManager, mm2: MarketManager):
        # get currency for each market
        mm1_currency = mm1.get_market_currency(self.TARGET_CURRENCY)
        mm2_currency = mm2.get_market_currency(self.TARGET_CURRENCY)

        # collect initial stack before going into trade loop
        logging.info("Collecting initial spread stack, please wait...")
        self.collect_initial_stack()
        logging.info("Done collecting! Current stack size: %d", self.spread_stack.size)

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

            # get previous mean, standard deviation
            mean = self.spread_stack.mean()
            stdev = self.spread_stack.std()

            # get upper & lower bound
            upper = mean + stdev * StatArbBot.Z_SCORE_SIGMA
            lower = mean - stdev * StatArbBot.Z_SCORE_SIGMA

            # get current spread
            cur_spread, mm1_last, mm2_last = Analyzer.get_ticker_log_spread(mm1, mm1_currency, mm2, mm2_currency)

            # log stat
            logging.info("[STAT] cur_spread: %.8f, mean: %.8f, stdev: %.8f" % (cur_spread, mean, stdev))

            # make decision
            if cur_spread < lower:
                logging.warning("[EXECUTE] New")
                # long in mm1, short in mm2
                mm1.order_buy(mm1_currency, mm1_last, self.COIN_TRADING_UNIT)
                mm2.order_sell(mm2_currency, mm2_last, self.COIN_TRADING_UNIT)

            elif cur_spread > upper:
                logging.warning("[EXECUTE] Reverse")
                # long in mm2, short in mm1
                mm2.order_buy(mm2_currency, mm2_last, self.COIN_TRADING_UNIT)
                mm1.order_sell(mm1_currency, mm1_last, self.COIN_TRADING_UNIT)

            else:
                logging.warning("[EXECUTE] No")

            # log combined balance
            Analyzer.log_combined_balance(mm1.get_balance(), mm2.get_balance())

            # remove the earliest spread in the stack
            self.spread_stack = np.delete(self.spread_stack, 0)

            # append the current spread
            self.spread_stack = np.append(self.spread_stack, cur_spread)

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)

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

        for co_item, kb_item in zip(co_cursor, kb_cursor):
            co_last = co_item["last"].to_decimal()
            kb_last = kb_item["last"].to_decimal()
            log_spread = math.log(co_last) - math.log(kb_last)
            self.spread_stack = np.append(self.spread_stack, log_spread)
