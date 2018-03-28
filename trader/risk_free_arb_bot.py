import time
import logging
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


class RiskFreeArbBot:
    TARGET_CURRENCY = "eth"
    COIN_TRADING_UNIT = 0.01
    TRADE_INTERVAL_IN_SEC = 3
    TARGET_STRATEGY = Analyzer.buy_sell_strategy_2
    NEW_SPREAD_THRESHOLD = 0
    REV_SPREAD_THRESHOLD = 0

    def __init__(self):
        # init market managers
        # self.coinone_mm = CoinoneMarketManager()
        # self.korbit_mm = KorbitMarketManager()
        self.v_coinone_mm = VirtualMarketManager("co", VirtualMarketApiType.COINONE, 0.001, 60000, 0.1)
        self.v_korbit_mm = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT, 0.0008, 60000, 0.1)

    def run(self):
        Global.configure_default_root_logging()
        self.execute(self.v_coinone_mm, self.v_korbit_mm, RiskFreeArbBot.TARGET_STRATEGY)

    def execute(self, mm1: MarketManager, mm2: MarketManager, strategy_fun):
        # get currency for each market
        mm1_currency = mm1.get_market_currency(self.TARGET_CURRENCY)
        mm2_currency = mm2.get_market_currency(self.TARGET_CURRENCY)

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

            # get current spread
            new_spread, rev_spread, mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price = \
                strategy_fun(mm1, mm1_currency, mm2, mm2_currency)

            # log stat
            logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (mm1.get_market_name(),
                                                                       mm1_buy_price, mm1_sell_price))
            logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (mm2.get_market_name(),
                                                                       mm2_buy_price, mm2_sell_price))
            logging.info("[STAT] new_spread: %d, rev_spread: %d" % (new_spread, rev_spread))

            # calculate needed krw
            mm1_buy_krw = mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm1_buy_price
            mm2_buy_krw = mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm2_buy_price

            # make decision
            if (
                    new_spread > self.NEW_SPREAD_THRESHOLD
                    and mm1.has_enough_coin("krw", mm1_buy_krw)
                    and mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
            ):
                logging.warning("[EXECUTE] New")
                mm1.order_buy(mm1_currency, mm1_buy_price, self.COIN_TRADING_UNIT)
                mm2.order_sell(mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)

            elif (
                    rev_spread > self.REV_SPREAD_THRESHOLD
                    and mm2.has_enough_coin("krw", mm2_buy_krw)
                    and mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
            ):
                logging.warning("[EXECUTE] Reverse")
                mm2.order_buy(mm2_currency, mm2_buy_price, self.COIN_TRADING_UNIT)
                mm1.order_sell(mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)

            else:
                logging.warning("[EXECUTE] No")

            # log combined balance
            Analyzer.log_combined_balance(mm1.get_balance(), mm2.get_balance())

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)


RiskFreeArbBot().run()
