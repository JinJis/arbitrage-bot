from pymongo.cursor import Cursor
from analyzer.analyzer import ATSAnalyzer
from analyzer.analyzer import BasicAnalyzer
from trader.market_manager.virtual_market_manager import VirtualMarketManager


class OpptyRequestTimeCollector:
    TARGET_STRATEGY = ATSAnalyzer.actual_tradable_spread_strategy
    INTERVAL = 5

    def __init__(self, mm1: VirtualMarketManager, mm2: VirtualMarketManager, target_currency: str):
        self.target_currency = target_currency
        self.mm1 = mm1
        self.mm2 = mm2
        self.raw_rq_time_dict = dict(new=[], rev=[])

    def run(self, mm1_data_cursor: Cursor, mm2_data_cursor: Cursor):

        # loop through history data
        for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
            self.add_oppty_requesttime_to_list(mm1_data, mm2_data)

        # sort raw rq time into duration
        new_oppty_duration = OpptyRequestTimeCollector.sort_by_time_duration(self.raw_rq_time_dict["new"])
        rev_oppty_duration = OpptyRequestTimeCollector.sort_by_time_duration(self.raw_rq_time_dict["rev"])
        return dict(new=new_oppty_duration, rev=rev_oppty_duration)

    def add_oppty_requesttime_to_list(self, mm1_data: dict, mm2_data: dict):
        new_unit_spread, rev_unit_spread = self.get_spread_info(mm1_data, mm2_data,
                                                                self.mm1.market_fee, self.mm2.market_fee)
        # collect requestTime when NEW
        if new_unit_spread > 0:
            self.raw_rq_time_dict["new"].append(mm1_data["requestTime"])

        # collect requestTime when NEW
        if rev_unit_spread > 0:
            self.raw_rq_time_dict["rev"].append(mm1_data["requestTime"])

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
        was_in_oppty = False
        temp_time_set = list()
        result = list()
        for index, item in enumerate(rq_time_list[1:]):
            now = rq_time_list[index + 1]
            before = rq_time_list[index]
            # when in oppty
            if now - before == cls.INTERVAL:
                if not was_in_oppty:
                    was_in_oppty = True
                    temp_time_set.append(before)
            # when not in oppty
            else:
                if was_in_oppty:
                    was_in_oppty = False
                    temp_time_set.append(before)
                    result.append([i for i in temp_time_set])
                    temp_time_set.clear()
        # when the last item is under oppty
        if was_in_oppty:
            temp_time_set.append(rq_time_list[-1])
            result.append([i for i in temp_time_set])
            temp_time_set.clear()
        return result

    @staticmethod
    def get_total_duration_time(result_dict: dict):
        total_duration = dict(new=0, rev=0)
        for key in result_dict.keys():
            for time in result_dict[key]:
                diff = time[1] - time[0]
                total_duration[key] += diff
        return total_duration
