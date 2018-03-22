import time
import logging
import numpy as np
from .market_manager.market_manager import MarketManager
from .market_manager.coinone_market_manager import CoinoneMarketManager
from .market_manager.korbit_market_manager import KorbitMarketManager
from .market.market import Market
from api.currency import Currency, KorbitCurrency, CoinoneCurrency
from config.global_conf import Global

"""
[NEW Spread] => buy in mm1, sell in mm2
[REVERSE Spread] => buy in mm2, sell in mm1
"""


class ArbitrageBot:
    TARGET_CURRENCY = "eth"
    BOLLINGER_TIME_STEP = 20
    Z_SIGMA = 1
    COIN_TRADING_UNIT = 0.01
    TRADE_INTERVAL_IN_SEC = 3

    def __init__(self):
        # init market managers
        self.coinone_mm = CoinoneMarketManager()
        self.korbit_mm = KorbitMarketManager()

        # init stack
        self.new_spread_stack = np.array([], dtype=np.float32)
        self.reverse_spread_stack = np.array([], dtype=np.float32)
        self.bolinger_spread_stack = np.array([], dtype=np.float32)

    def run(self):
        Global.configure_default_root_logging()
        self.execute_no_risk(self.coinone_mm, self.korbit_mm)

    def execute_no_risk(self, mm1: MarketManager, mm2: MarketManager):
        # get currency for each market
        mm1_currency = ArbitrageBot.get_market_currency(mm1, self.TARGET_CURRENCY)
        mm2_currency = ArbitrageBot.get_market_currency(mm2, self.TARGET_CURRENCY)

        while True:
            # get current spread
            current_new_spread, current_reverse_spread, mm1_minask_price, mm1_maxbid_price, \
            mm2_minask_price, mm2_maxbid_price = self.get_current_spread(mm1, mm1_currency, mm2, mm2_currency)

            # log stat
            logging.info(
                "[STAT] current_new: %s, current_reverse: %s" % (current_new_spread, current_reverse_spread)
            )

            # make decision
            if current_new_spread > 0:
                logging.warning("[EXECUTE] New")
                mm1.order_buy(mm1_currency, mm1_minask_price, self.COIN_TRADING_UNIT)
                mm2.order_sell(mm2_currency, mm2_maxbid_price, self.COIN_TRADING_UNIT)
            elif current_reverse_spread > 0:
                logging.warning("[EXECUTE] Reverse")
                mm2.order_buy(mm2_currency, mm2_minask_price, self.COIN_TRADING_UNIT)
                mm1.order_sell(mm1_currency, mm1_maxbid_price, self.COIN_TRADING_UNIT)
            else:
                logging.warning("[EXECUTE] No")

            # update balance
            mm1.update_balance()
            mm2.update_balance()

            # log balance
            logging.warning(
                "[BALANCE] %d KRW in %s, %d KRW in %s" %
                (mm1.get_market_tag().value, mm1.get_balance(), mm2.get_market_tag().value, mm2.get_balance())
            )

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)

    def execute_bollinger(self, mm1: MarketManager, mm2: MarketManager, stat_size):
        # get currency for each market
        mm1_currency = ArbitrageBot.get_market_currency(mm1, self.TARGET_CURRENCY)
        mm2_currency = ArbitrageBot.get_market_currency(mm2, self.TARGET_CURRENCY)

        # collect spread stack until the stack fills the stat_size
        while self.new_spread_stack.size < stat_size:
            logging.info(
                "[STACK] Skip until the spread stack gets to %d / %d" % (self.new_spread_stack.size, stat_size))
            self.collect_spread_stacks_for_bollinger(mm1, mm1_currency, mm2, mm2_currency)
            logging.info("[STACK] Spread stack size is now %d / %d" % (self.new_spread_stack.size, stat_size))

        # after the stack is filled
        while True:
            # calculate mov_ag & sigma
            new_mov_avg = self.new_spread_stack.mean()
            new_sigma = self.new_spread_stack.std()
            reverse_mov_avg = self.reverse_spread_stack.mean()
            reverse_sigma = self.reverse_spread_stack.std()

            # get current spread
            current_new_spread, current_reverse_spread, mm1_minask_price, mm1_maxbid_price, \
            mm2_minask_price, mm2_maxbid_price = self.get_current_spread(mm1, mm1_currency, mm2, mm2_currency)

            # log stats
            logging.info(
                "[STAT] new_mov_avg: %s, new_sigma: %s, current_new: %s" % (new_mov_avg, new_sigma, current_new_spread)
            )
            logging.info(
                "[STAT] reverse_mov_avg: %s, reverse_sigma: %s and current_reverse: %s" %
                (reverse_mov_avg, reverse_sigma, current_reverse_spread)
            )

            # make decision
            if current_new_spread > 0 and current_new_spread > new_mov_avg + new_sigma * self.Z_SIGMA:
                logging.warning("[EXECUTE] New")
                mm1.order_buy(mm1_currency, mm1_minask_price, self.COIN_TRADING_UNIT)
                mm2.order_sell(mm2_currency, mm2_maxbid_price, self.COIN_TRADING_UNIT)
            elif current_reverse_spread > 0 and current_reverse_spread > reverse_mov_avg + reverse_sigma * self.Z_SIGMA:
                logging.warning("[EXECUTE] Reverse")
                mm2.order_buy(mm2_currency, mm2_minask_price, self.COIN_TRADING_UNIT)
                mm1.order_sell(mm1_currency, mm1_maxbid_price, self.COIN_TRADING_UNIT)
            else:
                logging.warning("[EXECUTE] No")

            # update balance
            mm1.update_balance()
            mm2.update_balance()

            # log balance
            logging.warning(
                "[BALANCE] %d KRW in %s, %d KRW in %s" %
                (mm1.get_market_tag().value, mm1.get_balance(), mm2.get_market_tag().value, mm2.get_balance())
            )

            # remove the earliest spread in the stack
            self.new_spread_stack = np.delete(self.new_spread_stack, 0)
            self.reverse_spread_stack = np.delete(self.reverse_spread_stack, 0)

            # append the current spread
            self.new_spread_stack = np.append(self.new_spread_stack, current_new_spread)
            self.reverse_spread_stack = np.append(self.reverse_spread_stack, current_reverse_spread)

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)

    def collect_spread_stacks_for_bollinger(self, mm1: MarketManager, mm1_currency: Currency,
                                            mm2: MarketManager, mm2_currency: Currency):
        # request for current spread
        new_spread, reverse_spread, _, _, _, _ = self.get_current_spread(mm1, mm1_currency, mm2, mm2_currency)
        # add the spreads in respective stack
        self.new_spread_stack = np.append(self.new_spread_stack, new_spread)
        self.reverse_spread_stack = np.append(self.reverse_spread_stack, reverse_spread)

    @staticmethod
    def get_current_spread(mm1: MarketManager, mm1_currency: Currency, mm2: MarketManager, mm2_currency: Currency):
        mm1_orderbook = mm1.get_orderbook(mm1_currency)
        mm1_minask_price, mm1_maxbid_price = ArbitrageBot.get_price_of_minask_maxbid(mm1_orderbook)

        mm2_orderbook = mm1.get_orderbook(mm2_currency)
        mm2_minask_price, mm2_maxbid_price = ArbitrageBot.get_price_of_minask_maxbid(mm2_orderbook)

        logging.info("[%s] minask: %s, maxbid: %s" % (mm1.get_market_tag().value, mm1_minask_price, mm1_maxbid_price))
        logging.info("[%s] minask: %s, maxbid: %s" % (mm2.get_market_tag().value, mm2_minask_price, mm2_maxbid_price))

        new_spread = ArbitrageBot.calc_spread(mm1_minask_price, mm1.market_fee, mm2_maxbid_price, mm2.market_fee)
        reverse_spread = ArbitrageBot.calc_spread(mm2_minask_price, mm2.market_fee, mm1_maxbid_price, mm1.market_fee)

        return new_spread, reverse_spread, mm1_minask_price, mm1_maxbid_price, mm2_minask_price, mm2_maxbid_price

    @staticmethod
    def calc_spread(buy_price, buy_fee, sell_price, sell_fee):
        return (-1) * buy_price / (1 - buy_fee) + (+1) * sell_price * (1 - sell_fee)

    @staticmethod
    def get_market_currency(mm: MarketManager, target_currency: str):
        market_tag = mm.get_market_tag()
        if market_tag is Market.COINONE:
            currency = CoinoneCurrency[target_currency.upper()]
        elif market_tag is Market.KORBIT:
            currency = KorbitCurrency[target_currency.upper()]
        else:
            raise Exception("Invalid market tag!")
        return currency

    @staticmethod
    def get_price_of_minask_maxbid(orderbook: dict):
        return orderbook["asks"][0]["price"].to_decimal(), orderbook["bids"][0]["price"].to_decimal()
