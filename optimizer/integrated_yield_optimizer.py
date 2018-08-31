import copy
import logging
import configparser
import numpy as np
from pymongo.cursor import Cursor
from config.global_conf import Global
from analyzer.trade_analyzer import BasicAnalyzer, IYOAnalyzer
from config.shared_mongo_client import SharedMongoClient
from collector.oppty_time_collector import OpptyTimeCollector
from optimizer.base_optimizer import BaseOptimizer
from optimizer.initial_setting_optimizer import InitialSettingOptimizer
from optimizer.initial_balance_optimizer import InitialBalanceOptimizer

OTC = OpptyTimeCollector
ISO = InitialSettingOptimizer
IBO = InitialBalanceOptimizer


class IntegratedYieldOptimizer(BaseOptimizer):
    # default variables
    default_initial_setting_dict = {
        "max_trading_coin": 0.1,
        "min_trading_coin": 0,
        "new": {
            "threshold": 0
        },
        "rev": {
            "threshold": 0
        }
    }

    @classmethod
    def run(cls, settings: dict, bal_factor_settings: dict, factor_settings: dict,
            is_stat_appender: bool = False, is_slicing_dur: bool = False, slicing_interval: int = None):

        # get oppty_dur dict
        oppty_dur_dict = OTC.run(settings)
        logging.info("Total Oppty Duration Dict: %s" % oppty_dur_dict)

        # get oppty_dur in human date dict
        oppty_dur_human_dict = OTC.get_oppty_dur_human_time(oppty_dur_dict, timezone="kr")
        logging.info("Total Oppty Duration Human date Dict: %s" % oppty_dur_human_dict)

        # loop through oppty times

        # if parse oppty_dur by parsing_interval (usage for Trade Streamer
        if is_slicing_dur:

            sliced_oppty_dur_dict = cls.get_sliced_oppty_dur_dict(oppty_dur_dict, slicing_interval)
            return cls.run_iyo(settings, bal_factor_settings, factor_settings, sliced_oppty_dur_dict)

        # only use of data collecting of IYO or shallow analysis
        else:
            result = cls.run_iyo(settings, bal_factor_settings, factor_settings, oppty_dur_dict)

            if not is_stat_appender:
                return result
            else:
                return cls.run_iyo_stat_appender(result)

    @classmethod
    def run_iyo(cls, settings: dict, bal_factor_settings: dict, factor_settings: dict, oppty_dur_dict: dict):
        db_result = []
        for trade_type in ["new", "rev"]:
            for time in oppty_dur_dict[trade_type]:
                try:
                    # clone settings, balance factor settings, factor settings with original one
                    settings_clone = copy.deepcopy(settings)
                    bal_fact_set_clone = copy.deepcopy(bal_factor_settings)
                    fact_set_clone = copy.deepcopy(factor_settings)

                    # apply each oppty duration
                    settings_clone["start_time"] = time[0]
                    settings_clone["end_time"] = time[1]

                    # convert to local time
                    st_local = Global.convert_epoch_to_local_datetime(time[0], timezone="kr")
                    et_local = Global.convert_epoch_to_local_datetime(time[1], timezone="kr")
                    logging.error(
                        "Now in: [%s] start_time: %s, end_time: %s" % (trade_type.upper(), st_local, et_local))

                    # initial dry run -> get new, rev oppty count
                    new_oppty_count, rev_oppty_count = super().count_oppty_num(settings_clone,
                                                                               cls.default_initial_setting_dict)

                    # opt initial settings by oppty
                    fact_set_clone = cls.opt_factor_settings_by_oppty(fact_set_clone, new_oppty_count, rev_oppty_count)
                    # opt balance_settings by oppty
                    bal_fact_set_clone = cls.opt_balance_settings_by_oppty(bal_fact_set_clone, new_oppty_count,
                                                                           rev_oppty_count)

                    # create coin balance proportionate current exchange rate
                    bal_fact_set_clone = IBO.create_coin_bal_from_krw_bal_by_exchange_rate(settings_clone,
                                                                                           bal_fact_set_clone)

                    # add init step for balance settings and initial settings
                    cls.init_initial_step(settings_clone, bal_fact_set_clone, fact_set_clone)

                    # run recursive
                    iyo_opt_result = cls.opt_by_bal_and_init_settings_recursive(settings_clone, bal_fact_set_clone,
                                                                                fact_set_clone, settings_clone["depth"])

                    # append original oppty count to final result
                    iyo_opt_result["new_oppty_count"] = new_oppty_count
                    iyo_opt_result["rev_oppty_count"] = rev_oppty_count

                    db_result.append(iyo_opt_result)

                except Exception as e:
                    logging.error("Something went wrong while executing IYO loop!", time, e)

        # finally run IYO Stat appender and return final result
        return db_result

    @classmethod
    def init_initial_step(cls, settings: dict, bal_factor_settings: dict, factor_settings: dict):
        # set initial step for balance settings
        for market in bal_factor_settings.keys():
            for item in bal_factor_settings[market]:
                target_dict = bal_factor_settings[market][item]
                target_dict["step"] = super().calc_steps_under_limit(target_dict, settings["division"])

        # set initial step for factor settings
        flattened_items = ISO.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            item["step"] = super().calc_steps_under_limit(item, settings["division"])

    @classmethod
    def opt_by_bal_and_init_settings_recursive(cls, settings: dict, bal_factor_settings: dict,
                                               factor_settings: dict,
                                               depth: int, optimized: dict = None):
        if depth == 0:
            # log final Opt result yield
            final_opt_yield = optimized["yield"]
            logging.info("[IYO Final Opt Result]")
            logging.info(">>>[Final Optimized Info]: %s" % optimized)
            logging.error(">>>[Final Opted Yield]: %.4f%%" % final_opt_yield)

            return optimized

        logging.info("<<<< Now in [IYO] depth: %d >>>>" % depth)

        # init seq for balance settings
        for market in bal_factor_settings.keys():
            for item in bal_factor_settings[market]:
                target_dict = bal_factor_settings[market][item]
                target_dict["seq"] = super().generate_seq(target_dict["start"], target_dict["end"], target_dict["step"])

        # init seq for initial settings
        flattened_items = ISO.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            item["seq"] = super().generate_seq(item["start"], item["end"], item["step"])

        # execute tests with seq
        result = cls.test_trade_result_in_seq(settings, bal_factor_settings, factor_settings)

        # get opt
        # optimize in terms of yield
        cur_optimized = IYOAnalyzer.get_iyo_opt_yield_pair(result)

        if optimized is None:
            optimized = cur_optimized
        elif cur_optimized["yield"] > optimized["yield"]:
            optimized = cur_optimized

        # log current optimized yield
        logging.info("[IYO Depth:%d] Current Opted Yield: %.4f%%" % (depth, cur_optimized["yield"]))

        # reset start, end, step for both balance settings and initial settings
        division = settings["division"]
        bal_factor_settings = IBO.get_new_balance_settings(optimized["balance_setting"], bal_factor_settings, division)
        factor_settings = ISO.get_new_factor_settings(optimized["initial_setting"], factor_settings, division)

        depth -= 1
        return cls.opt_by_bal_and_init_settings_recursive(settings, bal_factor_settings, factor_settings,
                                                          depth, optimized)

    @classmethod
    def test_trade_result_in_seq(cls, settings: dict, bal_factor_settings: dict, factor_settings: dict):
        result = []
        # calc total odds
        iyo_total_odds = cls.calculate_iyo_total_odds(bal_factor_settings, factor_settings)

        # create balance settings and inital settings batch
        bal_setting_batch = IBO.create_balance_batch_from_seq(bal_factor_settings)
        initial_settings_batch = ISO.create_batch_initial_settings(factor_settings)

        iyo_index = 0
        # loop through IBO first
        for bal_setting in bal_setting_batch:
            for init_setting in initial_settings_batch:

                iyo_index += 1
                logging.info("Now conducting [IYO] %d out of %d" % (iyo_index, iyo_total_odds))

                # if total invested krw is 0, skip ISO (no trade anyway)
                if (bal_setting["mm1"]["krw_balance"] + bal_setting["mm2"]["krw_balance"]) == 0:
                    logging.info("Skipped [IYO] because total invested KRW was 0!")
                    continue

                # If not invested krw is 0
                # sync batch with settings to loop over
                cloned_settings = IBO.clone_settings_with_given_bal_setting(settings, bal_setting)

                # query data
                mm1_cursor, mm2_cursor = cls.get_history_data(cloned_settings)

                # init & run bot
                bot = super().create_bot(cloned_settings["mm1"], cloned_settings["mm2"],
                                         cloned_settings["target_currency"])
                bot.run(mm1_cursor, mm2_cursor, init_setting, is_running_in_optimizer=True)

                # append formatted data
                result.append(cls.get_combined_result(cloned_settings, init_setting, bal_setting, {
                    "total_krw_bal": bot.total_krw_bal,
                    "new_traded": bot.trade_new,
                    "rev_traded": bot.trade_rev,
                    "end_balance": {
                        "mm1": bot.mm1.vt_balance,
                        "mm2": bot.mm2.vt_balance
                    }
                }))

        return result

    @classmethod
    def calculate_iyo_total_odds(cls, bal_factor_settings: dict, factor_settings: dict):
        # calc IBO total odds
        ibo_total_odds = 1
        for market in bal_factor_settings.keys():
            sequence = bal_factor_settings[market]["krw_balance"]["seq"]
            ibo_total_odds *= len(sequence)
        # calc ISO total odds
        iso_total_odds = 1
        flattened_items = ISO.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            iso_total_odds *= len(item["seq"])
        # calc IYO total odds
        return ibo_total_odds * iso_total_odds

    @classmethod
    def get_combined_result(cls, settings: dict, init_setting: dict, bal_setting: dict, exec_result: dict):
        result = dict()
        # encode <Market.market_tag> of settings to string in order to save into Mongo DB
        cloned_settings = copy.deepcopy(settings)
        for market in ["mm1", "mm2"]:
            encoded_mkt_tag = cloned_settings[market]["market_tag"].value
            cloned_settings[market]["market_tag"] = encoded_mkt_tag

        # if new is dominant,
        if exec_result["rev_traded"] < exec_result["new_traded"]:
            result["total_krw_exhausted"] = bal_setting["mm1"]["krw_balance"] - exec_result["end_balance"]["mm1"]["krw"]

        # if rev is dominant,
        if exec_result["rev_traded"] > exec_result["new_traded"]:
            result["total_krw_exhausted"] = bal_setting["mm2"]["krw_balance"] - exec_result["end_balance"]["mm2"]["krw"]

        # if nothing traded,
        if exec_result["rev_traded"] == exec_result["new_traded"] == 0:
            result["total_krw_exhausted"] = 0

        result["krw_earned"] = exec_result["total_krw_bal"] - (
                bal_setting["mm1"]["krw_balance"] + bal_setting["mm2"]["krw_balance"])
        try:
            result["yield"] = (result["krw_earned"] / result["total_krw_exhausted"]) * 100
        except ZeroDivisionError:
            result["yield"] = 0

        result["new_traded"] = exec_result["new_traded"]
        result["rev_traded"] = exec_result["rev_traded"]
        result["end_balance"] = exec_result["end_balance"]
        result["settings"] = cloned_settings
        result["initial_setting"] = init_setting
        result["balance_setting"] = bal_setting

        return result

    @staticmethod
    def run_iyo_stat_appender(iyo_data_list: list):
        iyo_with_stat_list = []
        for iyo_data in iyo_data_list:
            logging.info("Now conducting IYO MongoDBAnalyzer for optimized IYO result!")
            iyo_data["stat"] = IYOStatAppender.run(iyo_data)
            iyo_with_stat_list.append(iyo_data)
        return iyo_with_stat_list

    @staticmethod
    def get_sliced_oppty_dur_dict(oppty_dur_dict: dict, slicing_interval: int):
        parsed_oppty_dur_dict = dict()
        for trade_type in ["new", "rev"]:
            result_list = []
            for time_list in oppty_dur_dict[trade_type]:
                start = None
                while True:
                    if start is None:
                        start = time_list[0]
                        continue
                    end = start + slicing_interval
                    if end <= time_list[1]:
                        result_list.append([start, end])
                        start = end
                        continue
                    else:
                        result_list.append([start, time_list[1]])
                        break
            parsed_oppty_dur_dict[trade_type] = result_list
        return parsed_oppty_dur_dict


# This Analyzer is for analyzing and calculating statistical infos in IYO mongoDB data
class IYOStatAppender:
    @classmethod
    def run(cls, iyo_data: dict):

        # convert infos in IYO_data to usable format
        mm1: str = cls.configure_market(iyo_data["settings"]["mm1"]["market_tag"])
        mm2: str = cls.configure_market(iyo_data["settings"]["mm2"]["market_tag"])
        coin: str = iyo_data["settings"]["target_currency"]
        start_time: int = iyo_data["settings"]["start_time"]
        end_time: int = iyo_data["settings"]["end_time"]

        # <Inner Oppty Duration Stats>
        mm1_cur, mm2_cur = cls.get_orderbook_cursor(mm1, mm2, coin, start_time, end_time)
        inner_stats_result = cls.get_inner_oppty_dur_stats(mm1_cur, mm2_cur)

        # <Outer Oppty Duration Stats>
        outer_stats_result = cls.get_outer_oppty_dur_stats(mm1, mm2, coin, start_time)

        # return as dict combinded with inner_stats_result and outer_stats_result
        return dict(inner_oppty=inner_stats_result, outer_oppty=outer_stats_result)

    @staticmethod
    def configure_market(setting_mkt: str):
        # create configParser to convert settings market
        config = configparser.ConfigParser()
        config.read("config/conf_iyo_market.ini")
        return str(config.get("IYO", setting_mkt))

    @classmethod
    def get_orderbook_cursor(cls, mm1: str, mm2: str, coin_name: str, start_time: int, end_time: int):
        db_client = SharedMongoClient.instance()
        mm1_col = db_client[mm1][coin_name + "_orderbook"]
        mm2_col = db_client[mm2][coin_name + "_orderbook"]
        return SharedMongoClient.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

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
    def get_outer_oppty_dur_stats(cls, mm1: str, mm2: str, coin: str, oppty_start_time: int):
        outer_stats = {
            "5min_before": {},
            "10min_before": {},
            "30min_before": {}
        }

        for roll_back_time in [5, 10, 30]:
            outer_mm1_ob_cur, outer_mm2_ob_cur \
                = cls.get_orderbook_cursor(mm1, mm2, coin,
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
        IYOStatAppender.calc_avg_var_std_data(target_dict[mkt_tag]["mid_price"], mid_price_list)

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
    def calc_avg_var_std_data(target_dict: dict, data_list: list):
        target_dict["avg"] = round(float(np.average(data_list)), 8)
        target_dict["var"] = round(float(np.var(data_list)), 8)
        target_dict["std"] = round(float(np.std(data_list)), 8)
        target_dict["data"] = data_list
