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
        self.v_coinone_mm = VirtualMarketManager("co", VirtualMarketApiType.COINONE, 0.001, 60000, 0.1)
        self.v_korbit_mm = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT, 0.0008, 60000, 0.1)

        # init stack
        self.new_spread_stack = np.array([], dtype=np.float32)
        self.reverse_spread_stack = np.array([], dtype=np.float32)
        self.bolinger_spread_stack = np.array([], dtype=np.float32)

        # init balance
        self.mm1_balance = None
        self.mm2_balance = None

    def run(self):
        Global.configure_default_root_logging()
        self.execute_no_risk(self.v_coinone_mm, self.v_korbit_mm)

    def execute_no_risk(self, mm1: MarketManager, mm2: MarketManager):
        # update balance
        mm1.update_balance()
        mm2.update_balance()
        self.mm1_balance = mm1.get_balance()
        self.mm2_balance = mm2.get_balance()

        # log initial balance
        logging.info("[INITIAL BALANCE]")
        logging.info(self.mm1_balance)
        logging.info(self.mm2_balance)

        # get currency for each market
        mm1_currency = mm1.get_market_currency(self.TARGET_CURRENCY)
        mm2_currency = mm2.get_market_currency(self.TARGET_CURRENCY)

        while True:
            # print a blank line
            logging.info("")

            # get current spread
            new_spread, rev_spread, mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price = \
                Analyzer.buy_sell_strategy_1(mm1, mm1_currency, mm2, mm2_currency)

            # log stat
            logging.info(
                "[STAT][%s] buy_price: %d, sell_price: %d" % (mm1.name, mm1_buy_price, mm1_sell_price))
            logging.info(
                "[STAT][%s] buy_price: %d, sell_price: %d" % (mm2.name, mm2_buy_price, mm2_sell_price))
            logging.info("[STAT] new_spread: %d, rev_spread: %d" % (new_spread, rev_spread))

            mm1_buy_cost = mm1_buy_price * mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)
            mm2_buy_cost = mm2_buy_price * mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)

            # make decision
            if (new_spread > 0 and self.mm1_balance.get_available_krw() > mm1_buy_cost
                    and self.mm2_balance.get_available_eth() > self.COIN_TRADING_UNIT):

                logging.warning("[EXECUTE] New")
                mm1.order_buy(mm1_currency, mm1_buy_price, self.COIN_TRADING_UNIT)
                mm2.order_sell(mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)

            elif (rev_spread > 0 and self.mm2_balance.get_available_krw() > mm2_buy_cost
                  and self.mm1_balance.get_available_eth() > self.COIN_TRADING_UNIT):

                logging.warning("[EXECUTE] Reverse")
                mm2.order_buy(mm2_currency, mm2_buy_price, self.COIN_TRADING_UNIT)
                mm1.order_sell(mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)

            else:
                logging.warning("[EXECUTE] No")

            # update balance
            mm1.update_balance()
            mm2.update_balance()
            self.mm1_balance = mm1.get_balance()
            self.mm2_balance = mm2.get_balance()

            # log balance
            logging.info(self.mm1_balance)
            logging.info(self.mm2_balance)

            for coin in ("eth", "krw"):
                mm1_coin_balance = self.mm1_balance.to_dict()[coin]
                mm2_coin_balance = self.mm2_balance.to_dict()[coin]

                logging.warning("[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                                (coin.upper(), mm1_coin_balance["available"] + mm2_coin_balance["available"],
                                 mm1_coin_balance["trade_in_use"] + mm2_coin_balance["trade_in_use"],
                                 mm1_coin_balance["balance"] + mm2_coin_balance["balance"]))

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)


ArbitrageBot().run()
