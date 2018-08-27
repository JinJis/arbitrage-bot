import copy
import logging
from config.shared_mongo_client import SharedMongoClient
from analyzer.trade_analyzer import BasicAnalyzer, IBOAnalyzer
from optimizer.base_optimizer import BaseOptimizer
from backtester.risk_free_arb_backtester import RfabBacktester


class InitialBalanceOptimizer(BaseOptimizer):
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
    def run(cls, settings: dict, bal_factor_settings: dict):

        # initial dry run
        logging.warning("Now optimizing balance settings by oppty!!")
        (new_oppty_count, rev_oppty_count) = cls.count_oppty_num(settings, cls.default_initial_setting_dict)
        bal_factor_settings = super().opt_balance_settings_by_oppty(bal_factor_settings,
                                                                    new_oppty_count, rev_oppty_count)

        # create coin_balance that is proportionate to krw_balance size
        bal_factor_settings = cls.create_coin_bal_from_krw_bal_by_exchange_rate(settings, bal_factor_settings)

        # set initial step for balance settings
        for market in bal_factor_settings.keys():
            for item in bal_factor_settings[market]:
                target_dict = bal_factor_settings[market][item]
                target_dict["step"] = super().calc_steps_under_limit(target_dict, settings["division"])

        # run recursive
        return cls.opt_by_balance_settings_recursive(settings, bal_factor_settings, settings["depth"])

    @classmethod
    def create_coin_bal_from_krw_bal_by_exchange_rate(cls, settings: dict, bal_factor_settings: dict):
        # get coin-krw exchange rate
        exchange_rate = cls.calc_krw_coin_exchange_ratio_during_oppty_dur(settings)  # (krw / 1 coin)

        clone = copy.deepcopy(bal_factor_settings)
        for item in ["start", "step_limit"]:
            clone["mm1"]["coin_balance"][item] = round(clone["mm2"]["krw_balance"][item] / exchange_rate, 5)
            clone["mm2"]["coin_balance"][item] = round(clone["mm1"]["krw_balance"][item] / exchange_rate, 5)

        # check if inject COIN_SEQ_END is more or less that that of injected KRW_SEQ_END injected
        for standard_mm, opposite_mm in zip(["mm1", "mm2"], ["mm2", "mm1"]):
            standard_mm_krw_in_coin_end = (clone[standard_mm]["krw_balance"]["end"] / exchange_rate)
            opposite_mm_coin_end = clone[opposite_mm]["coin_balance"]["end"]

            if standard_mm_krw_in_coin_end > opposite_mm_coin_end:
                clone[standard_mm]["krw_balance"]["end"] = int(opposite_mm_coin_end * exchange_rate)
            else:
                clone[opposite_mm]["coin_balance"]["end"] = round(standard_mm_krw_in_coin_end, 5)

        return clone

    @staticmethod
    def calc_krw_coin_exchange_ratio_during_oppty_dur(settings: dict):
        mm1_col = SharedMongoClient.get_target_col(settings["mm1"]["market_tag"], settings["target_currency"])
        mm2_col = SharedMongoClient.get_target_col(settings["mm2"]["market_tag"], settings["target_currency"])
        mm1_cursor, mm2_cursor = SharedMongoClient.get_data_from_db(mm1_col, mm2_col,
                                                                    settings["start_time"], settings["end_time"])

        # get average mid exchange krw price in terms of unit coin during designated time_dur
        mid_price_list = []
        for mm1_data, mm2_data in zip(mm1_cursor, mm2_cursor):
            mm1_mid_price, _, _, = BasicAnalyzer.get_orderbook_mid_price(mm1_data)
            mm2_mid_price, _, _, = BasicAnalyzer.get_orderbook_mid_price(mm2_data)
            combined_mid_price = (mm1_mid_price + mm2_mid_price) / 2
            mid_price_list.append(combined_mid_price)
        return sum(mid_price_list) / len(mid_price_list)

    @classmethod
    def opt_by_balance_settings_recursive(cls, settings: dict, bal_factor_settings: dict, depth: int,
                                          optimized: dict = None):
        if depth == 0:
            final_opt_yield = optimized["yield"]
            logging.critical("\n[IBO Final Opt Result]"
                             "\n>>>Final Opted Yield: %.4f%%"
                             "\n>>>Final Optimized Info: %s" % (final_opt_yield, optimized))
            return optimized

        logging.critical("\n<<<< Now in [IBO] depth: %d >>>>" % depth)

        # init seq
        for market in bal_factor_settings.keys():
            for item in bal_factor_settings[market]:
                target_dict = bal_factor_settings[market][item]
                target_dict["seq"] = super().generate_seq(target_dict["start"], target_dict["end"], target_dict["step"])

        # execute tests with seq
        result = cls.test_trade_result_in_seq(settings, bal_factor_settings)
        """
            <data structure>
            1)  result = [combined_dict, combined_dict, combined_dict, ... ]
            2)  combined_dict or cur_optimized = {
                    "total_krw_invested: float,
                    "krw_earned": float,                
                    "yield" : float,
                    "new_num": int, 
                    "rev_num": int, 
                    "balance_setting": dict
                }
        """

        # get opt
        # optimize in terms of yield
        cur_optimized = IBOAnalyzer.get_opt_yield_pair(result)

        if optimized is None:
            optimized = cur_optimized
        elif cur_optimized["yield"] > optimized["yield"]:
            optimized = cur_optimized

        # log current optimized yield
        logging.critical("[IBO Depth:%d] Current Opted Yield: %.4f%%" % (depth, cur_optimized["yield"]))

        # reset start, end, step
        division = settings["division"]
        bal_factor_settings = cls.get_new_balance_settings(optimized["balance_setting"], bal_factor_settings, division)

        depth -= 1
        return cls.opt_by_balance_settings_recursive(settings, bal_factor_settings, depth, optimized)

    @classmethod
    def test_trade_result_in_seq(cls, settings: dict, bal_factor_settings: dict):
        result = []
        # calc total odds
        total_odds = 1
        for market in bal_factor_settings.keys():
            sequence = bal_factor_settings[market]["krw_balance"]["seq"]
            total_odds *= len(sequence)

        # create balance settings batch
        bal_setting_batch = cls.create_balance_batch_from_seq(bal_factor_settings)

        index = 0
        for bal_setting in bal_setting_batch:
            index += 1
            logging.warning("Now conducting [IBO] %d out of %d" % (index, total_odds))

            # if total invested krw is 0, skip (no trade anyway)
            if (bal_setting["mm1"]["krw_balance"] + bal_setting["mm2"]["krw_balance"]) == 0:
                logging.warning("ISO skipped because total invested KRW is 0!")
                continue

            # sync batch with settings to loop over
            cloned_settings = cls.clone_settings_with_given_bal_setting(settings, bal_setting)

            # query data
            mm1_cursor, mm2_cursor = cls.get_history_data(cloned_settings)

            # opt_factor = [krw_bal_after, factor_Settings, new # , rev #]
            bot = super().create_bot(cloned_settings["mm1"], cloned_settings["mm2"], cloned_settings["target_currency"])
            # in IBO, init_factor_setting is fixed and balance_setting is subject to change
            bot.run(mm1_cursor, mm2_cursor, cls.default_initial_setting_dict, True)
            # combine opted_factor_settings returned and bal_settings into dict
            combined_dict = cls.combine_balance_settings_in_dict(bal_setting, bot)
            result.append(combined_dict)

        return result

    @classmethod
    def get_new_balance_settings(cls, opt_balance_settings: dict, bal_factor_settings: dict, division: int):
        opt = opt_balance_settings
        pre = bal_factor_settings
        clone = copy.deepcopy(bal_factor_settings)

        for market in bal_factor_settings.keys():
            for key in bal_factor_settings[market]:
                clone[market][key] = cls.get_new_factor_settings_item(opt[market][key], pre[market][key], division)
        return clone

    @staticmethod
    def get_new_factor_settings_item(current_opt, factor_item: dict, division: int):

        prev_start = factor_item["start"]
        prev_end = factor_item["end"]
        prev_step = factor_item["step"]

        if prev_start >= prev_end:
            return factor_item

        # if used in IBO, initial seq end set by IYO config for krw and coin should be fixed,
        # since this amount will be interpreted as the maximum balance used in trading.
        if prev_end == current_opt:
            clone = copy.deepcopy(factor_item)
            clone["end"] = current_opt
            clone["start"] = current_opt - 2 * prev_step
            clone["step"] = (clone["end"] - clone["start"]) / division
            return clone

        clone = copy.deepcopy(factor_item)
        clone["start"] = current_opt - prev_step
        if clone["start"] < 0:
            clone["start"] = 0
        clone["end"] = current_opt + prev_step
        clone["step"] = (clone["end"] - clone["start"]) / division
        return clone

    @classmethod
    def create_balance_batch_from_seq(cls, bal_factor_settings: dict):
        result = []

        # since mm1_krw - mm2_coin & mm1_coin - mm2_krw go together, use enumerate
        # By doing this, can enhance speed of calc and reduce odds significantly
        for mm1_krw, mm2_coin in zip(bal_factor_settings["mm1"]["krw_balance"]["seq"],
                                     bal_factor_settings["mm2"]["coin_balance"]["seq"]):
            for mm2_krw, mm1_coin in zip(bal_factor_settings["mm2"]["krw_balance"]["seq"],
                                         bal_factor_settings["mm1"]["coin_balance"]["seq"]):
                result.append({
                    "mm1": {
                        "krw_balance": mm1_krw,
                        "coin_balance": mm1_coin
                    },
                    "mm2": {
                        "krw_balance": mm2_krw,
                        "coin_balance": mm2_coin
                    }
                })
        return result

    @classmethod
    def combine_balance_settings_in_dict(cls, bal_settings: dict, bot: RfabBacktester):
        combined_dict = dict()
        combined_dict["total_krw_invested"] = bal_settings["mm1"]["krw_balance"] + bal_settings["mm2"]["krw_balance"]
        combined_dict["krw_earned"] = bot.total_krw_bal - combined_dict["total_krw_invested"]
        combined_dict["yield"] = combined_dict["krw_earned"] / combined_dict["total_krw_invested"] * 100
        combined_dict["new_num"] = bot.trade_new
        combined_dict["rev_num"] = bot.trade_rev
        combined_dict["balance_setting"] = bal_settings
        return combined_dict

    @staticmethod
    def clone_settings_with_given_bal_setting(settings: dict, bal_setting: dict):
        clone = copy.deepcopy(settings)
        for market in bal_setting.keys():
            for bal_type in bal_setting[market]:
                clone[market][bal_type] = bal_setting[market][bal_type]
        return clone
