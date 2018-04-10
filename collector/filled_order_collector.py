from api.coinone_api import CoinoneApi, CoinoneCurrency
from api.korbit_api import KorbitApi, KorbitCurrency
from analyzer.filled_order_analyzer import FilledOrderAnalyzer
from pymongo import MongoClient


class FilledOrderCollector:
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
        self.co_filled_orders_col = self.co_db[currency + "_filled_orders"]

        # init korbit related
        self.kb_api = KorbitApi.instance(is_public_access_only=True)
        self.kb_db = self.client["korbit"]
        self.kb_currency = KorbitCurrency[currency.upper()]
        self.kb_filled_orders_col = self.kb_db[currency + "_filled_orders"]

        # init last_* for record
        self.last_kb_fo = None
        self.last_kb_ob = None

    def collect_kb_filled_orders(self):
        cur_kb_ob = self.kb_api.get_orderbook(self.kb_currency)
        cur_kb_fo = self.kb_api.get_filled_orders(self.kb_currency, "minute")
        # clone cur_kb_fo for last_kb_fo record
        # since we are directly setting take type on cur_kb_fo
        # and get_filled_orders_within needs to take unaltered fo data
        clone_kb_fo = list(cur_kb_fo)

        if (self.last_kb_ob is not None) and (self.last_kb_fo is not None):
            fo_within = FilledOrderAnalyzer.get_filled_orders_within(self.last_kb_fo, cur_kb_fo)
            FilledOrderAnalyzer.set_take_type_from_orderbook(fo_within, self.last_kb_ob)
            print(fo_within)

        self.last_kb_ob = cur_kb_ob
        self.last_kb_fo = clone_kb_fo
