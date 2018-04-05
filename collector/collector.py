from api.coinone_api import CoinoneApi, CoinoneCurrency
from api.korbit_api import KorbitApi, KorbitCurrency
from pymongo import MongoClient
import logging


class Collector:
    def __init__(self, mongodb_uri: str, currency: str):
        # make sure currency is in lower-case format
        if not currency.islower():
            raise Exception("<currency> parameter should be a lower-cased symbol of the target currency!")

        # init mongo client
        self.client = MongoClient(mongodb_uri)

        # init coinone related
        self.co_api = CoinoneApi.instance(is_public_access_only=True)
        self.co_db = self.client["coinone"]
        self.co_currency = CoinoneCurrency[currency.upper()]
        self.co_ticker_col = self.co_db[currency + "_ticker"]
        self.co_orderbook_col = self.co_db[currency + "_orderbook"]
        self.co_ma_mb_col = self.co_db[currency + "_ma_mb"]
        self.co_filled_orders_col = self.co_db[currency + "_filled_orders"]

        # init korbit related
        self.kb_api = KorbitApi.instance(is_public_access_only=True)
        self.kb_db = self.client["korbit"]
        self.kb_currency = KorbitCurrency[currency.upper()]
        self.kb_ticker_col = self.kb_db[currency + "_ticker"]
        self.kb_orderbook_col = self.kb_db[currency + "_orderbook"]
        self.kb_ma_mb_col = self.kb_db[currency + "_ma_mb"]
        self.kb_filled_orders_col = self.kb_db[currency + "_filled_orders"]

        # init last_* for fallback
        self.last_co_ticker = dict()
        self.last_co_orderbook = dict()
        self.last_kb_ticker = dict()
        self.last_kb_orderbook = dict()

    def collect_co_ticker(self, request_time: int):
        co_ticker = None
        # noinspection PyBroadException
        try:
            co_ticker = self.co_api.get_ticker(self.co_currency)
        except Exception:
            co_ticker = self.last_co_ticker
            logging.exception("collect_co_ticker")
        finally:
            co_ticker["requestTime"] = request_time
            # need to copy the mutable dict because in `insert`,
            # mongo is adding `_id` property, which would eventually cause DuplicateKeyError
            self.last_co_ticker = dict(co_ticker)
            self.co_ticker_col.insert_one(co_ticker)

    def collect_co_orderbook(self, request_time: int):
        co_orderbook = None
        # noinspection PyBroadException
        try:
            co_orderbook = self.co_api.get_orderbook(self.co_currency)
        except Exception:
            co_orderbook = self.last_co_orderbook
            logging.exception("collect_co_orderbook")
        finally:
            co_orderbook["requestTime"] = request_time
            self.last_co_orderbook = dict(co_orderbook)
            self.co_orderbook_col.insert_one(co_orderbook)
            co_ma_mb = {
                "timestamp": co_orderbook["timestamp"],
                "minAsk": co_orderbook["asks"][0],
                "maxBid": co_orderbook["bids"][0],
                "requestTime": request_time
            }
            self.co_ma_mb_col.insert_one(co_ma_mb)

    def collect_co_filled_orders(self):
        co_filled_orders = self.co_api.get_filled_orders(self.co_currency)
        self.co_filled_orders_col.insert_many(co_filled_orders)

    def collect_kb_ticker(self, request_time: int):
        kb_ticker = None
        # noinspection PyBroadException
        try:
            kb_ticker = self.kb_api.get_ticker(self.kb_currency)
        except Exception:
            kb_ticker = self.last_kb_ticker
            logging.exception("collect_kb_ticker")
        finally:
            kb_ticker["requestTime"] = request_time
            self.last_kb_ticker = dict(kb_ticker)
            self.kb_ticker_col.insert_one(kb_ticker)

    def collect_kb_orderbook(self, request_time: int):
        kb_orderbook = None
        # noinspection PyBroadException
        try:
            kb_orderbook = self.kb_api.get_orderbook(self.kb_currency)
        except Exception:
            kb_orderbook = self.last_kb_orderbook
            logging.exception("collect_kb_orderbook")
        finally:
            kb_orderbook["requestTime"] = request_time
            self.last_kb_orderbook = dict(kb_orderbook)
            self.kb_orderbook_col.insert_one(kb_orderbook)
            kb_ma_mb = {
                "timestamp": kb_orderbook["timestamp"],
                "minAsk": kb_orderbook["asks"][0],
                "maxBid": kb_orderbook["bids"][0],
                "requestTime": request_time
            }
            self.kb_ma_mb_col.insert_one(kb_ma_mb)

    def collect_kb_filled_orders(self):
        kb_filled_orders = self.kb_api.get_filled_orders(self.kb_currency)
        self.kb_filled_orders_col.insert_many(kb_filled_orders)
