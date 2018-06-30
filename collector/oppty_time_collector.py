from pymongo.cursor import Cursor
from analyzer.analyzer import ATSAnalyzer
from analyzer.analyzer import BasicAnalyzer
from trader.market_manager.virtual_market_manager import VirtualMarketManager


class OpptyTimeCollector:
    TARGET_STRATEGY = ATSAnalyzer.actual_tradable_spread_strategy
    CONSECUTION_GRACE_TIME = 60

    def __init__(self, target_currency: str, mm1: VirtualMarketManager, mm2: VirtualMarketManager):
        self.target_currency = target_currency
        self.mm1 = mm1
        self.mm2 = mm2

    def run(self, mm1_data_cursor: Cursor, mm2_data_cursor: Cursor):
        # loop through history data
        raw_rq_time_dict = dict(new=[], rev=[])
        for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
            # get spread
            new_unit_spread, rev_unit_spread = self.get_spread_info(mm1_data, mm2_data,
                                                                    self.mm1.market_fee, self.mm2.market_fee)
            # collect requestTime when NEW
            if new_unit_spread > 0:
                raw_rq_time_dict["new"].append(mm1_data["requestTime"])

            # collect requestTime when NEW
            if rev_unit_spread > 0:
                raw_rq_time_dict["rev"].append(mm1_data["requestTime"])

        # sort raw rq time into duration
        new_oppty_duration = OpptyTimeCollector.sort_by_time_duration(raw_rq_time_dict["new"])
        rev_oppty_duration = OpptyTimeCollector.sort_by_time_duration(raw_rq_time_dict["rev"])
        return dict(new=new_oppty_duration, rev=rev_oppty_duration)

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

    @classmethod
    def sort_by_time_duration(cls, rq_time_list: list):
        result = list()
        start = None
        prev = None
        for index, item in enumerate(rq_time_list):
            if prev is None:
                start = item
                prev = item
                continue
            current = item
            if (current - prev) > cls.CONSECUTION_GRACE_TIME:
                end = prev
                result.append([start, end])
                start = current
            prev = current
        return result

    @staticmethod
    def get_total_duration_time(result_dict: dict):
        total_duration = dict(new=0, rev=0)
        for key in result_dict.keys():
            for time in result_dict[key]:
                diff = time[1] - time[0]
                total_duration[key] += diff
        return total_duration
