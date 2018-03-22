import time
import json
import logging
import numpy as np
import urllib.request
from .market_manager.market_manager import MarketManager
from .market_manager.coinone_market_manager import CoinoneMarketManager
from .market_manager.korbit_market_manager import KorbitMarketManager
from .market.market import Market
from api.currency import Currency, KorbitCurrency, CoinoneCurrency
from config.global_conf import Global
from bson import Decimal128
from decimal import Decimal

"""
[NEW Spread] => buy in mm1, sell in mm2
[REVERSE Spread] => buy in mm2, sell in mm1
"""


class ArbitrageBot:
    TARGET_CURRENCY = "eth"
    BOLLINGER_TIME_STEP = 20
    Z_SIGMA = 1
    COIN_TRADING_UNIT = 0.01

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

    def collect_spread_stacks_for_bollinger(self, mm1: MarketManager, mm1_currency: Currency,
                                            mm2: MarketManager, mm2_currency: Currency):
        # request for current spread
        new_spread, reverse_spread, _, _, _, _ = self.get_current_spread(mm1, mm1_currency, mm2, mm2_currency)
        # add the spreads in respective stack
        self.new_spread_stack = np.append(self.new_spread_stack, new_spread)
        self.reverse_spread_stack = np.append(self.reverse_spread_stack, reverse_spread)

    def execute_no_risk(self, mm1: MarketManager, mm2: MarketManager):
        # get currency for each market
        mm1_currency = ArbitrageBot.get_market_currency(mm1, self.TARGET_CURRENCY)
        mm2_currency = ArbitrageBot.get_market_currency(mm2, self.TARGET_CURRENCY)

        new_spread, reverse_spread, _, _, _, _ = self.get_current_spread(mm1, mm1_currency, mm2, mm2_currency)

        print("new_mov_avg: %s, new_sigma: %s and current_new: %s" % (new_mov_avg, new_sigma, current_new_spread))
        print("reverse_mov_avg: %s, reverse_sigma: %s and current_reverse: %s" \
              % (reverse_mov_avg, reverse_sigma, current_reverse_spread))

        if current_new_spread > 0:
            print("[new]")
            b_market.buy(volume=0.03, bid_price=hoga_b["minask"])
            a_market.sell(volume=0.03, ask_price=hoga_a["maxbid"])
        elif current_reverse_spread > 0:
            print("[reverse]")
            a_market.buy(volume=0.03, bid_price=hoga_a["minask"])
            b_market.sell(volume=0.03, ask_price=hoga_b["maxbid"])
        else:
            print("[No]")

        #         total_krw = a_market.balance_total(hoga_a["maxbid"]) + b_market.balance_total(hoga_b["maxbid"])
        print("[Total krw: %s\n" % (self.total_krw_balance()))

        self.new_spread_stack = np.delete(self.new_spread_stack, 0)
        self.reverse_spread_stack = np.delete(self.reverse_spread_stack, 0)
        self.new_spread_stack = np.append(self.new_spread_stack, current_new_spread)
        self.reverse_spread_stack = np.append(self.reverse_spread_stack, current_reverse_spread)

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

    def get_profit_amount(self, buy_idx, sell_idx, buy_depth, sell_depth, buy_fee, sell_fee):
        if self.get_spread(sell_depth["bids"][sell_idx]["price"], sell_fee, buy_depth["asks"][buy_idx]["price"],
                           buy_fee) <= 0:
            return 0, 0

        max_amount_buy = 0
        for i in range(buy_idx + 1):
            max_amount_buy += buy_depth["asks"][i]["amount"]
        max_amount_sell = 0
        for j in range(sell_idx + 1):
            max_amount_sell += sell_depth["bids"][j]["amount"]
        max_amount = min(max_amount_buy, max_amount_sell)

        buy_total = 0
        avg_buyprice = 0
        for i in range(buy_idx + 1):
            price = buy_depth["asks"][i]["price"]
            amount = min(max_amount, buy_total + buy_depth["asks"][i]["amount"]) - buy_total
            if amount <= 0:
                break
            buy_total += amount
            if avg_buyprice == 0 or buy_total == 0:
                avg_buyprice = price
            else:
                avg_buyprice = (avg_buyprice * (buy_total - amount) + price * amount) / buy_total

        sell_total = 0
        avg_sellprice = 0
        for j in range(sell_idx + 1):
            price = sell_depth["bids"][j]["price"]
            amount = min(max_amount, sell_total + sell_depth["bids"][j]["amount"]) - sell_total
            if amount <= 0:
                break
            sell_total += amount
            if avg_sellprice == 0 or sell_total == 0:
                avg_sellprice = price
            else:
                avg_sellprice = (avg_sellprice * (sell_total - amount) + price * amount) / sell_total

        profit = sell_total * avg_sellprice * (1 - sell_fee) - buy_total * avg_buyprice * (1 + buy_fee)
        return profit, max_amount

    def get_max_depth_idx(self, buy_depth, sell_depth, buy_fee, sell_fee):
        buy_idx, sell_idx = 0, 0
        while self.get_spread(sell_depth["bids"][0]["price"], sell_fee, buy_depth["asks"][buy_idx]["price"],
                              buy_fee) > 0:
            buy_idx += 1
        while self.get_spread(sell_depth["bids"][sell_idx]["price"], sell_fee, buy_depth["asks"][0]["price"],
                              buy_fee) > 0:
            sell_idx += 1
        return buy_idx, sell_idx

    def get_idx_amount(self, buy_depth, sell_depth, buy_fee, sell_fee):
        max_buy_idx, max_sell_idx = self.get_max_depth_idx(buy_depth, sell_depth, buy_fee, sell_fee)
        max_amount = 0
        best_profit = 0
        best_buy_idx, best_sell_idx = 0, 0
        for buy_idx in range(max_buy_idx + 1):
            for sell_idx in range(max_sell_idx + 1):
                profit, amount = self.get_profit_amount(buy_idx, sell_idx, buy_depth, sell_depth, buy_fee, sell_fee)
                if profit >= 0 and profit >= best_profit:
                    best_profit = profit
                    max_amount = amount
                    best_buy_idx, best_sell_idx = buy_idx, sell_idx
        return best_buy_idx, best_sell_idx, max_amount

    def get_depth_api(self, url):
        req = urllib.request.Request(url, None, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent": "curl"})
        res = urllib.request.urlopen(req)
        if (res == None):
            return None
        depth = json.loads(res.read().decode('utf8'))
        return depth

    def execute_bollinger(self):


t = ArbitrageBot()
t.test()
