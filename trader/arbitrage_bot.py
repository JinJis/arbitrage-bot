import time
import logging
import numpy as np
from trader.market_manager.market_manager import MarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.virtual_market_manager import VirtualMarketManager, VirtualMarketApiType
from config.global_conf import Global
from analyzer.analyzer import Analyzer

"""
!!! IMPORTANT NOTE !!!

[NEW Spread] => buy in mm1, sell in mm2
[REV Spread] => buy in mm2, sell in mm1

MODIFY config.global_conf > COIN_FILTER_FOR_BALANCE for balance creation!
"""


class ArbitrageBot:
    TARGET_CURRENCY = "eth"
    COIN_TRADING_UNIT = 0.02
    TRADE_INTERVAL_IN_SEC = 3

    def __init__(self):
        # init market managers
        # self.coinone_mm = CoinoneMarketManager()
        # self.korbit_mm = KorbitMarketManager()
        self.v_coinone_mm = VirtualMarketManager("co", VirtualMarketApiType.COINONE)
        self.v_korbit_mm = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT)

        # init stack
        self.new_spread_stack = np.array([], dtype=np.float32)
        self.reverse_spread_stack = np.array([], dtype=np.float32)
        self.bolinger_spread_stack = np.array([], dtype=np.float32)

    def run(self):
        Global.configure_default_root_logging()
        self.execute_no_risk(self.v_coinone_mm, self.v_korbit_mm)

    def execute_no_risk(self, mm1: MarketManager, mm2: MarketManager):
        # log initial balance
        logging.warning("[INITIAL BALANCE]")
        logging.warning(mm1.get_balance())
        logging.warning(mm2.get_balance())

        # get currency for each market
        mm1_currency = mm1.get_market_currency(self.TARGET_CURRENCY)
        mm2_currency = mm2.get_market_currency(self.TARGET_CURRENCY)

        while True:
            # get current spread
            new_spread, rev_spread, mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price = \
                Analyzer.buy_sell_strategy_1(mm1, mm1_currency, mm2, mm2_currency)

            # log stat
            logging.info(
                "[STAT][%s] buy_price: %d, sell_price: %d" % (mm1.get_market_tag(), mm1_buy_price, mm1_sell_price))
            logging.info(
                "[STAT][%s] buy_price: %d, sell_price: %d" % (mm2.get_market_tag(), mm2_buy_price, mm2_sell_price))
            logging.info("[STAT] new_spread: %s, rev_spread: %s" % (new_spread, rev_spread))

            # make decision
            if new_spread > 0:
                logging.warning("[EXECUTE] New")
                mm1.order_buy(mm1_currency, mm1_buy_price, self.COIN_TRADING_UNIT)
                mm2.order_sell(mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
            elif rev_spread > 0:
                logging.warning("[EXECUTE] Reverse")
                mm2.order_buy(mm2_currency, mm2_buy_price, self.COIN_TRADING_UNIT)
                mm1.order_sell(mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)
            else:
                logging.warning("[EXECUTE] No")

            # update balance
            mm1.update_balance()
            mm2.update_balance()

            # calculate balance
            mm1_balance = mm1.get_balance()
            mm2_balance = mm2.get_balance()
            mm1_krw_balance = mm1.get_balance().to_dict()["krw"]
            mm2_krw_balance = mm2.get_balance().to_dict()["krw"]

            # log balance
            logging.warning("[BALANCE]")
            logging.warning(mm1_balance)
            logging.warning(mm2_balance)
            logging.warning("[TOTAL KRW]: available - %d KRW, trade_in_use - %d KRW, balance - %d KRW" %
                            (mm1_krw_balance["available"] + mm2_krw_balance["available"],
                             mm1_krw_balance["trade_in_use"] + mm2_krw_balance["trade_in_use"],
                             mm1_krw_balance["balance"] + mm2_krw_balance["balance"]))

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)

ArbitrageBot().run()