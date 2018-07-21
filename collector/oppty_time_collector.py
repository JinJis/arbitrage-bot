from analyzer.analyzer import BasicAnalyzer
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.virtual_market_manager import VirtualMarketManager


class OpptyTimeCollector:
    # default CONSECUTION_GRACE_TIME
    CONSECUTION_GRACE_TIME = 60

    @classmethod
    def run(cls, settings: dict):

        # sync CONSECUTION_GRACE_TIME
        cls.CONSECUTION_GRACE_TIME = settings["consecution_time"]

        # initiate Market / Mongo settings
        mm1, mm2, mm1_data_cursor, mm2_data_cursor = cls.initiate_market_mongo_settings(settings)

        # loop through history data
        raw_rq_time_dict = dict(new=[], rev=[])
        for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
            # get spread
            new_unit_spread, rev_unit_spread = cls.get_spread_info(mm1_data, mm2_data, mm1.market_fee, mm2.market_fee)
            # collect requestTime when NEW
            if new_unit_spread > 0:
                raw_rq_time_dict["new"].append(mm1_data["requestTime"])

            # collect requestTime when NEW
            if rev_unit_spread > 0:
                raw_rq_time_dict["rev"].append(mm1_data["requestTime"])

        # sort raw rq time into duration
        new_oppty_duration = OpptyTimeCollector.sort_by_consecutive_time_duration(raw_rq_time_dict["new"])
        rev_oppty_duration = OpptyTimeCollector.sort_by_consecutive_time_duration(raw_rq_time_dict["rev"])
        return dict(new=new_oppty_duration, rev=rev_oppty_duration)

    @staticmethod
    def initiate_market_mongo_settings(settings: dict):
        target_currency = settings["target_currency"]
        mm1 = VirtualMarketManager(settings["mm1"]["market_tag"], settings["mm1"]["fee_rate"],
                                   settings["mm1"]["krw_balance"], settings["mm1"]["coin_balance"],
                                   target_currency)
        mm2 = VirtualMarketManager(settings["mm2"]["market_tag"], settings["mm2"]["fee_rate"],
                                   settings["mm2"]["krw_balance"], settings["mm2"]["coin_balance"],
                                   target_currency)
        mm1_col = SharedMongoClient.get_target_col(settings["mm1"]["market_tag"], target_currency)
        mm2_col = SharedMongoClient.get_target_col(settings["mm2"]["market_tag"], target_currency)
        mm1_data_cursor, mm2_data_cursor = SharedMongoClient.get_data_from_db(mm1_col, mm2_col, settings["start_time"],
                                                                              settings["end_time"])
        return mm1, mm2, mm1_data_cursor, mm2_data_cursor

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
    def sort_by_consecutive_time_duration(cls, rq_time_list: list):
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
                diff = (time[1] - time[0])
                total_duration[key] += diff
        return total_duration
