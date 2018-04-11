import threading
from trader.market.market import Market


class GlobalFeeAccumulator:
    markets = dict()
    lock = threading.Lock()

    @classmethod
    def initialize_market(cls, market: Market):
        cls.markets[market.value] = {
            "krw": 0,
            "eth": 0
        }

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
