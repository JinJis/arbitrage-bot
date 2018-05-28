import threading
from trader.market.market import Market
from config.global_conf import Global


class GlobalFeeAccumulator:
    markets = dict()
    lock = threading.Lock()

    @classmethod
    def initialize_market(cls, market: Market):
        fee_tracker = dict()
        for coin in Global.COIN_FILTER_FOR_BALANCE:
            fee_tracker[coin] = 0
        cls.markets[market.value] = fee_tracker

    @classmethod
    def add_fee_expenditure(cls, market: Market, currency: str, fee: float):
        with cls.lock:
            cls.markets[market.value][currency] += fee

    @classmethod
    def sub_fee_consideration(cls, market: Market, currency: str, fee: float):
        with cls.lock:
            cls.markets[market.value][currency] -= fee

    @classmethod
    def get_fee(cls, market: Market, currency: str):
        return cls.markets[market.value][currency]
