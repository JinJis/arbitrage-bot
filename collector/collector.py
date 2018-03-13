from api.coinone_api import CoinoneApi, CoinoneCurrency
from api.korbit_api import KorbitApi, KorbitCurrency
from pymongo import MongoClient
import schedule
import functools
import time


def catch_exceptions(cancel_on_failure=False):
    def catch_exceptions_decorator(job_func):
        @functools.wraps(job_func)
        def wrapper(*args, **kwargs):
            try:
                return job_func(*args, **kwargs)
            except:
                import traceback
                print("Error at " + time.ctime())
                print(traceback.format_exc())
                if cancel_on_failure:
                    return schedule.CancelJob
        return wrapper
    return catch_exceptions_decorator


class Collector:
    def __init__(self, currency: str):
        # make sure currency is in lower-case format
        if not currency.islower():
            raise Exception("<currency> parameter should be a lower-cased symbol of the target currency!")

        # init mongo client
        self.client = MongoClient("127.0.0.1", 27017)

        # init coinone related
        self.co_api = CoinoneApi()
        self.co_db = self.client["coinone"]
        self.co_currency = CoinoneCurrency[currency.upper()].value
        self.co_ticker_col = self.co_db[currency + "_ticker"]
        self.co_orderbook_col = self.co_db[currency + "_orderbook"]
        self.co_ma_mb_col = self.co_db[currency + "_ma_mb"]
        self.co_filled_orders_col = self.co_db[currency + "_filled_orders"]

        # init korbit related
        self.kb_api = KorbitApi()
        self.kb_db = self.client["korbit"]
        self.kb_currency = KorbitCurrency[currency.upper()].value
        self.kb_ticker_col = self.kb_db[currency + "_ticker"]
        self.kb_orderbook_col = self.kb_db[currency + "_orderbook"]
        self.kb_ma_mb_col = self.kb_db[currency + "_ma_mb"]
        self.kb_filled_orders_col = self.kb_db[currency + "_filled_orders"]

    @catch_exceptions()
    def collect_co_ticker(self):
        co_ticker = self.co_api.get_ticker(self.co_currency)
        self.co_ticker_col.insert_one(co_ticker)

    @catch_exceptions()
    def collect_co_orderbook(self):
        co_orderbook = self.co_api.get_orderbook(self.co_currency)
        self.co_orderbook_col.insert_one(co_orderbook)
        co_ma_mb = {
            "timestamp": co_orderbook["timestamp"],
            "minAsk": co_orderbook["asks"][0],
            "maxBid": co_orderbook["bids"][0]
        }
        self.co_ma_mb_col.insert_one(co_ma_mb)

    @catch_exceptions()
    def collect_co_filled_orders(self):
        co_filled_orders = self.co_api.get_filled_orders(self.co_currency, "hour")
        self.co_filled_orders_col.insert_many(co_filled_orders)

    @catch_exceptions()
    def collect_kb_ticker(self):
        kb_ticker = self.kb_api.get_ticker(self.kb_currency)
        self.kb_ticker_col.insert_one(kb_ticker)

    @catch_exceptions()
    def collect_kb_orderbook(self):
        kb_orderbook = self.kb_api.get_orderbook(self.kb_currency)
        self.kb_orderbook_col.insert_one(kb_orderbook)
        kb_ma_mb = {
            "timestamp": kb_orderbook["timestamp"],
            "minAsk": kb_orderbook["asks"][0],
            "maxBid": kb_orderbook["bids"][0]
        }
        self.kb_ma_mb_col.insert_one(kb_ma_mb)

    @catch_exceptions()
    def collect_kb_filled_orders(self):
        kb_filled_orders = self.kb_api.get_filled_orders(self.kb_currency, "hour")
        self.kb_filled_orders_col.insert_many(kb_filled_orders)
