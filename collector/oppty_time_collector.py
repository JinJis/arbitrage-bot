from pymongo.cursor import Cursor
from analyzer.analyzer import ATSAnalyzer
from analyzer.analyzer import BasicAnalyzer
from trader.market_manager.virtual_market_manager import VirtualMarketManager


class OpptyRequestTimeCollector:
    TARGET_STRATEGY = ATSAnalyzer.actual_tradable_spread_strategy

    def __init__(self, mm1: VirtualMarketManager, mm2: VirtualMarketManager, target_currency: str):
        self.target_currency = target_currency
        self.mm1 = mm1
        self.mm2 = mm2
        self.result = dict(new=[], rev=[])

    def run(self, mm1_data_cursor: Cursor, mm2_data_cursor: Cursor):

        # loop through history data
        for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
            self.check_oppty_by_unit_spread(mm1_data, mm2_data)

        print(self.result)

    def check_oppty_by_unit_spread(self, mm1_data: dict, mm2_data: dict):
        # adjust orderbook for realistic backtesting
        self.mm1.apply_history_to_orderbook(mm1_data)
        self.mm2.apply_history_to_orderbook(mm2_data)

        new_unit_spread, rev_unit_spread = self.get_spread_info(mm1_data, mm2_data,
                                                                self.mm1.market_fee, self.mm2.market_fee)

        # NEW
        if new_unit_spread > 0:
            self.result["new"].append(mm1_data["requestTime"])
            if not mm1_data["requestTime"] == mm2_data["requestTime"]:
                print("mm1: %s & mm2: %s reqeustTime not matched" % (mm1_data["requestTime"], mm2_data["requestTime"]))

        # REVERSE
        if rev_unit_spread > 0:
            self.result["rev"].append(mm1_data["requestTime"])
            if not mm1_data["requestTime"] == mm2_data["requestTime"]:
                print("mm1: %s & mm2: %s reqeustTime not matched" % (mm1_data["requestTime"], mm2_data["requestTime"]))

    @classmethod
    def get_spread_info(cls, mm1_orderbook: dict, mm2_orderbook: dict, mm1_market_fee: float, mm2_market_fee: float):

        # mm1 price
        mm1_minask_price, mm1_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(mm1_orderbook)
        # mm2 price
        mm2_minask_price, mm2_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(mm2_orderbook)

        # new => buy in mm1, sell in mm2
        new_unit_spread = cls.get_unit_spread_info(mm1_minask_price, mm1_market_fee, mm2_maxbid_price, mm2_market_fee)
        # rev => buy in mm2, sell in mm1
        rev_unit_spread = cls.get_unit_spread_info(mm2_minask_price, mm2_market_fee, mm1_maxbid_price, mm1_market_fee)

        return new_unit_spread, rev_unit_spread

    @staticmethod  # avail_amount = total amount of coin that specific mkt provides
    def get_unit_spread_info(buy_unit_price: int, buy_fee: float, sell_unit_price: int, sell_fee: float):
        unit_spread = (-1) * buy_unit_price / (1 - buy_fee) + (+1) * sell_unit_price * (1 - sell_fee)
        return unit_spread
