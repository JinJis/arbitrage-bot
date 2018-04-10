from analyzer.filled_order_analyzer import FilledOrderAnalyzer
from pymongo.collection import Collection
from api.market_api import MarketApi
from api.currency import Currency


class FilledOrderCollector:
    def __init__(self, api: MarketApi, currency: Currency, target_col: Collection):
        self.api = api
        self.currency = currency
        self.target_col = target_col

        # init last_* for record
        self.last_ob = None
        self.last_fo = None

    def collect_filled_orders(self):
        cur_ob = self.api.get_orderbook(self.currency)
        cur_fo = self.api.get_filled_orders(self.currency, "minute")

        if (self.last_ob is not None) and (self.last_fo is not None):
            fo_within = FilledOrderAnalyzer.get_filled_orders_within(self.last_fo, cur_fo)
            FilledOrderAnalyzer.set_take_type_from_orderbook(fo_within, self.last_ob)
            print(fo_within)

        self.last_ob = cur_ob
        self.last_fo = cur_fo
