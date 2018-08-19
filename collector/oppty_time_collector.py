import logging
from config.global_conf import Global
from analyzer.trade_analyzer import BasicAnalyzer
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.virtual_market_manager import VirtualMarketManager


class OpptyTimeCollector:

    @classmethod
    def run(cls, settings: dict):

        # sync CONSECUTION_GRACE_TIME
        cls.CONSECUTION_GRACE_TIME = settings["consecution_time"]

        # initiate Market / Mongo settings
        mm1, mm2, mm1_data_cursor, mm2_data_cursor = cls.initiate_market_mongo_settings(settings)

        # loop through history data
        raw_rq_time_dict = dict(new=[], rev=[])
        for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
            # skip if either of orderbook data is empty
            if (not mm1_data) or (not mm1_data["asks"]) or (not mm1_data["bids"]):
                logging.info("mm1_data is empty! Skipping current item... %s" %
                             mm1_data["requestTime"] if mm1_data else "")
                continue
            if (not mm2_data) or (not mm2_data["asks"]) or (not mm2_data["bids"]):
                logging.info("mm2_data is empty! Skipping current item... %s" %
                             mm2_data["requestTime"] if mm2_data else "")
                continue

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
        mm1 = VirtualMarketManager(settings["mm1"]["market_tag"], settings["mm1"]["taker_fee"],
                                   settings["mm1"]["maker_fee"], settings["mm1"]["min_trading_coin"],
                                   settings["mm1"]["krw_balance"], settings["mm1"]["coin_balance"],
                                   target_currency, is_using_taker_fee=True)
        mm2 = VirtualMarketManager(settings["mm2"]["market_tag"], settings["mm2"]["taker_fee"],
                                   settings["mm2"]["maker_fee"], settings["mm2"]["min_trading_coin"],
                                   settings["mm2"]["krw_balance"], settings["mm2"]["coin_balance"],
                                   target_currency, is_using_taker_fee=True)
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
            if (current - prev) > getattr(cls, "CONSECUTION_GRACE_TIME"):
                end = prev
                result.append([start, end])
                start = current
            prev = current
        # if oppty continued from start til end but not caught by consecution_grace_time, return original
        if (len(result) == 0) and (not len(rq_time_list) == 0):
            result = [[rq_time_list[0], rq_time_list[-1]]]
        return result

    @staticmethod
    def get_total_duration_time(result_dict: dict):
        total_duration = dict(new=0, rev=0)
        for key in result_dict.keys():
            for time in result_dict[key]:
                diff = (time[1] - time[0])
                total_duration[key] += diff
        return total_duration

    @staticmethod
    def get_oppty_dur_human_time(oppty_dur_dict: dict, timezone: str):
        final_dict = dict()
        for key in oppty_dur_dict.keys():
            result_list = []
            for time_dur in oppty_dur_dict[key]:
                human_st = Global.convert_epoch_to_local_datetime(time_dur[0], timezone=timezone)
                human_et = Global.convert_epoch_to_local_datetime(time_dur[1], timezone=timezone)
                result_list.append([human_st, human_et])
            final_dict[key] = result_list

        return final_dict
