from analyzer.filled_order_analyzer import FilledOrderAnalyzer
from pymongo.database import Database
from api.market_api import MarketApi
from api.currency import Currency
import logging


class Collector:
    def __init__(self, api: MarketApi, currency: Currency, target_db: Database):
        self.api = api
        self.currency = currency

        currency_lc = currency.name.lower()
        self.ticker_col = target_db[currency_lc + "_ticker"]
        self.orderbook_col = target_db[currency_lc + "_orderbook"]
        self.filled_orders_col = target_db[currency_lc + "_filled_orders"]

        # init last_* as fallback for errors
        self.last_ticker = dict()
        self.last_orderbook = dict()

        # init last_* for record
        # this is for collect_filled_orders
        self.last_fo_ob = None
        self.last_fo = None

    def collect_ticker(self, request_time: int):
        ticker = None
        # noinspection PyBroadException
        try:
            ticker = self.api.get_ticker(self.currency)
        except Exception:
            ticker = self.last_ticker
            logging.exception("collect_co_ticker")
        finally:
            ticker["requestTime"] = request_time
            # need to copy the mutable dict because in `insert`,
            # mongo is adding `_id` property, which would eventually cause DuplicateKeyError
            self.last_ticker = dict(ticker)
            self.ticker_col.insert_one(ticker)

    def collect_orderbook(self, request_time: int):
        orderbook = None
        # noinspection PyBroadException
        try:
            orderbook = self.api.get_orderbook(self.currency)
        except Exception:
            orderbook = self.last_orderbook
            logging.exception("collect_co_orderbook")
        finally:
            orderbook["requestTime"] = request_time
            self.last_orderbook = dict(orderbook)
            self.orderbook_col.insert_one(orderbook)

    def collect_filled_orders(self):
        cur_fo_ob = self.api.get_orderbook(self.currency)
        # only korbit supports "minute" but we are using the param for all api anyway
        # note that coinone's default param uses "hour"
        cur_fo = self.api.get_filled_orders(self.currency, "minute")

        if (self.last_fo_ob is not None) and (self.last_fo is not None):
            fo_within = FilledOrderAnalyzer.get_filled_orders_within(self.last_fo, cur_fo)
            FilledOrderAnalyzer.set_take_type_from_orderbook(fo_within, self.last_fo_ob)
            # if the list is not empty
            if fo_within:
                self.filled_orders_col.insert_many(fo_within)

        self.last_fo_ob = cur_fo_ob
        self.last_fo = cur_fo
