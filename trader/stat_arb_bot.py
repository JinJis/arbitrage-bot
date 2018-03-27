import time
import logging
import numpy as np
from trader.market_manager.market_manager import MarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.virtual_market_manager import VirtualMarketManager, VirtualMarketApiType
from config.global_conf import Global
from analyzer.analyzer import Analyzer


class StatArbBot:
    TARGET_CURRENCY = "eth"
    COIN_TRADING_UNIT = 0.01
    TRADE_INTERVAL_IN_SEC = 3
    TARGET_SPREAD_STACK_SIZE = (60 / TRADE_INTERVAL_IN_SEC) * 60 * 3  # 3-hour data
    Z_SCORE_SIGMA = 2

    def __init__(self):
        # init market managers
        # self.coinone_mm = CoinoneMarketManager()
        # self.korbit_mm = KorbitMarketManager()
        self.v_coinone_mm = VirtualMarketManager("co", VirtualMarketApiType.COINONE, 0.001, 60000, 0.1)
        self.v_korbit_mm = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT, 0.0008, 60000, 0.1)

        # init stack
        self.spread_stack = np.array([], dtype=np.float32)

        # init balance
        self.mm1_balance = None
        self.mm2_balance = None

    def run(self):
        Global.configure_default_root_logging()
        self.execute(self.v_coinone_mm, self.v_korbit_mm)

    def execute(self, mm1: MarketManager, mm2: MarketManager):
        # get currency for each market
        mm1_currency = mm1.get_market_currency(self.TARGET_CURRENCY)
        mm2_currency = mm2.get_market_currency(self.TARGET_CURRENCY)

        self.update_and_log_balance(mm1, mm2)

        # TODO: get initial stack

        while True:
            # print a blank line
            logging.info("")

            # get previous mean, standard deviation
            mean = self.spread_stack.mean()
            stdev = self.spread_stack.std()

            # get upper & lower bound
            upper = mean + stdev * StatArbBot.Z_SCORE_SIGMA
            lower = mean - stdev * StatArbBot.Z_SCORE_SIGMA

            # get current spread
            cur_spread, mm1_last, mm2_last = Analyzer.get_ticker_log_spread(mm1, mm1_currency, mm2, mm2_currency)
            self.spread_stack = np.append(self.spread_stack, cur_spread)

            # log stat
            logging.info("[STAT] current spread (mm1 - mm2): %d" % cur_spread)

            # get buy cost
            mm1_buy_cost = mm1_last * mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)
            mm2_buy_cost = mm2_last * mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)


            # decide whether long, short
            if cur_spread < lower:
                # long in mm1, short in mm2
                mm1.order_buy(mm1_currency, mm1_buy_price, self.COIN_TRADING_UNIT)
                mm2.order_sell(mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)

            # make decision
            if (new_spread > 500 and self.mm1_balance.get_available_krw() > mm1_buy_cost
                    and self.mm2_balance.get_available_eth() > self.COIN_TRADING_UNIT):

                logging.warning("[EXECUTE] New")


            elif (rev_spread > 500 and self.mm2_balance.get_available_krw() > mm2_buy_cost
                  and self.mm1_balance.get_available_eth() > self.COIN_TRADING_UNIT):

                logging.warning("[EXECUTE] Reverse")
                mm2.order_buy(mm2_currency, mm2_buy_price, self.COIN_TRADING_UNIT)
                mm1.order_sell(mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)

            else:
                logging.warning("[EXECUTE] No")

            self.update_and_log_balance(mm1, mm2)

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)

    def update_and_log_balance(self, mm1: MarketManager, mm2: MarketManager):
        # update balance
        mm1.update_balance()
        mm2.update_balance()
        self.mm1_balance = mm1.get_balance()
        self.mm2_balance = mm2.get_balance()

        # log initial balance
        logging.info(self.mm1_balance)
        logging.info(self.mm2_balance)

        for coin in ("eth", "krw"):
            mm1_coin_balance = self.mm1_balance.to_dict()[coin]
            mm2_coin_balance = self.mm2_balance.to_dict()[coin]

            logging.warning("[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                            (coin.upper(), mm1_coin_balance["available"] + mm2_coin_balance["available"],
                             mm1_coin_balance["trade_in_use"] + mm2_coin_balance["trade_in_use"],
                             mm1_coin_balance["balance"] + mm2_coin_balance["balance"]))
