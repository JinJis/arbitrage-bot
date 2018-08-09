import numpy as np
from pymongo.cursor import Cursor
from pymongo.collection import Collection
from config.shared_mongo_client import SharedMongoClient
from analyzer.trade_analyzer import BasicAnalyzer


# This Analyzer is for analyzing and calculating statistical infos in IYO mongoDB data
class IYOMongoDBAnalyzer:
    """Exchange MKTs"""
    mkt_tag = {"Virtual_CO": "coinone",
               "Virtual_KB": "korbit",
               "Virtual_GP": "gopax"
               }

    @classmethod
    def run(cls, iyo_data: dict):
        # get needed infos in the iyo_data
        mm1_name: str = cls.mkt_tag[iyo_data["settings"]["mm1"]["market_tag"]]
        mm2_name: str = cls.mkt_tag[iyo_data["settings"]["mm2"]["market_tag"]]
        coin_name: str = iyo_data["settings"]["target_currency"]
        start_time: int = iyo_data["settings"]["start_time"]
        end_time: int = iyo_data["settings"]["end_time"]

        # get orderbook from each needed infos
        db_client = SharedMongoClient.instance()
        mm1_col = db_client[mm1_name][coin_name + "_orderbook"]
        mm2_col = db_client[mm2_name][coin_name + "_orderbook"]
        mm1_ob_cur, mm2_ob_cur = SharedMongoClient.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

        # <Inner Oppty Duration Stats>
        inner_stats_result = cls.get_inner_oppty_dur_stats(mm1_ob_cur, mm2_ob_cur)
        # Additionally get exhaust rate for mm1 & mm2 balance
        inner_stats_result["exhaus_rate"] = cls.calc_exhaust_rate(iyo_data)

        # <Outer Oppty Duration Stats>
        outer_stats_result = cls.get_outer_oppty_dur_stats(mm1_col, mm2_col, start_time)

        # return as dict combinded with inner_stats_result and outer_stats_result
        return dict(inner_stat=inner_stats_result, outer_stat=outer_stats_result)

    @classmethod
    def get_inner_oppty_dur_stats(cls, mm1_ob_cur: Cursor, mm2_ob_cur: Cursor):

        # set default structire for inner_stats
        inner_stats = {
            "mm1": {
                "mid_price": {},
                "amount": {
                    "asks": {
                        "min_ask": {},
                        "top5": {},
                        "top10": {},
                        "total": {}
                    },
                    "bids": {
                        "max_bid": {},
                        "top5": {},
                        "top10": {},
                        "total": {}
                    }
                }
            },
            "mm2": {
                "mid_price": {},
                "amount": {
                    "asks": {
                        "min_ask": {},
                        "top5": {},
                        "top10": {},
                        "total": {}
                    },
                    "bids": {
                        "max_bid": {},
                        "top5": {},
                        "top10": {},
                        "total": {}
                    }
                }
            }
        }  # avg, var, std will be added to each of deepest key
        # get mm1 stat infos
        cls.get_mid_price_stat("mm1", mm1_ob_cur.clone(), inner_stats)

        # get mm2 stat infos
        cls.get_mid_price_stat("mm2", mm2_ob_cur.clone(), inner_stats)

        # get mm1 amount stat infos
        cls.get_amount_stat_by_depth("mm1", mm1_ob_cur.clone(), inner_stats, "asks")
        cls.get_amount_stat_by_depth("mm1", mm1_ob_cur.clone(), inner_stats, "bids")

        # get mm2 amount stat infos
        cls.get_amount_stat_by_depth("mm2", mm2_ob_cur.clone(), inner_stats, "asks")
        cls.get_amount_stat_by_depth("mm2", mm2_ob_cur.clone(), inner_stats, "bids")

        return inner_stats

    @classmethod
    def get_outer_oppty_dur_stats(cls, mm1_col: Collection, mm2_col: Collection, oppty_start_time: int):
        outer_stats = {
            "5min_before": {},
            "10min_before": {},
            "30min_before": {}
        }
        for roll_back_time in [5, 10, 30]:
            outer_mm1_ob_cur, outer_mm2_ob_cur \
                = SharedMongoClient.get_data_from_db(mm1_col, mm2_col,
                                                     oppty_start_time - (roll_back_time * 60), oppty_start_time)

            # RECYCLE inner_oppty_dur_stats b/c data structure is identical
            inner_stats = cls.get_inner_oppty_dur_stats(outer_mm1_ob_cur, outer_mm2_ob_cur)

            # append inner_stats to outer_stats keys of [5, 10, 30min before]
            outer_stats["%dmin_before" % roll_back_time] = inner_stats

        return outer_stats

    @staticmethod
    def get_mid_price_stat(mkt_tag: str, orderbook_cur: Cursor, target_dict: dict):
        mid_price_list = []
        for orderbook in orderbook_cur:
            mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(orderbook)
            mid_price_list.append(mid_price)
        # append mid_price avg, var, st.d to inner_infos_dict
        IYOMongoDBAnalyzer.calc_avg_var_std_data(target_dict[mkt_tag]["mid_price"], mid_price_list)

    @classmethod
    def get_amount_stat_by_depth(cls, mkt_tag: str, orderbook_cur: Cursor, target_dict: dict, order_type: str):

        # create ma or mb, top5 index, top10 index, total index list
        ma_mb_amt_list = []
        top_five_amt_list = []
        top_ten_amt_list = []
        total_amt_list = []

        for orderbook in orderbook_cur:
            amount_sum = 0
            max_amt_index = len(orderbook[order_type])
            for i in range(max_amt_index):
                amount_sum += float(orderbook[order_type][i]["amount"].to_decimal())

                # append current min_ask or max_bid to proper list
                if i == 0:
                    ma_mb_amt_list.append(round(amount_sum, 8))
                # if iterating 5th, 10th, and last index of amount
                if i == 4:
                    top_five_amt_list.append(round(amount_sum, 8))
                if i == 9:
                    top_ten_amt_list.append(round(amount_sum, 8))
                if i == (max_amt_index - 1):
                    total_amt_list.append(round(amount_sum, 8))
                else:
                    continue

        # calc avg, var, std and append to each of "amount" section
        if order_type == "asks":
            cls.calc_avg_var_std_data(target_dict[mkt_tag]["amount"][order_type]["min_ask"], ma_mb_amt_list)
        elif order_type == "bids":
            cls.calc_avg_var_std_data(target_dict[mkt_tag]["amount"][order_type]["max_bid"], ma_mb_amt_list)
        else:
            raise Exception("Invalid marktet tag!! Must be one of 'asks' or 'bids'")

        cls.calc_avg_var_std_data(target_dict[mkt_tag]["amount"][order_type]["top5"], top_five_amt_list)
        cls.calc_avg_var_std_data(target_dict[mkt_tag]["amount"][order_type]["top10"], top_ten_amt_list)
        cls.calc_avg_var_std_data(target_dict[mkt_tag]["amount"][order_type]["total"], total_amt_list)

    @staticmethod
    def calc_exhaust_rate(iyo_data: dict):
        # when new, calc mm1 krw
        if (iyo_data["rev_traded"] == 0) and (iyo_data["new_traded"] != 0):
            start_bal = iyo_data["settings"]["mm1"]["krw_balance"]
            end_bal = iyo_data["end_balance"]["mm1"]["krw"]
            return round(((start_bal - end_bal) / start_bal * 100), 4)

        # when rev, calc mm2 krw
        if (iyo_data["new_traded"] == 0) and (iyo_data["rev_traded"] != 0):
            start_bal = iyo_data["settings"]["mm2"]["krw_balance"]
            end_bal = iyo_data["end_balance"]["mm2"]["krw"]
            return round(((start_bal - end_bal) / start_bal * 100), 4)
        else:
            raise Exception("Both of NEW and REV must be 0 or traded at least once")

    @staticmethod
    def calc_avg_var_std_data(target_dict: dict, data_list: list):
        target_dict["avg"] = round(float(np.average(data_list)), 8)
        target_dict["var"] = round(float(np.var(data_list)), 8)
        target_dict["std"] = round(float(np.std(data_list)), 8)
        target_dict["data"] = data_list
