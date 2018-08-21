import copy
import logging
from analyzer.trade_analyzer import ISOAnalyzer
from backtester.risk_free_arb_backtester import RfabBacktester
from optimizer.base_optimizer import BaseOptimizer


class InitialSettingOptimizer(BaseOptimizer):
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
    def run(cls, settings: dict, factor_settings: dict):
        # intial dry run
        (new_oppty_count, rev_oppty_count) = cls.count_oppty_num(settings, cls.default_initial_setting_dict,
                                                                 is_using_taker_fee=True)
        factor_settings = super().opt_factor_settings_by_oppty(factor_settings, new_oppty_count, rev_oppty_count)
        # set initial step
        flattened_items = cls.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            item["step"] = super().calc_steps_under_limit(item, settings["division"])

        # run recursive
        return cls.opt_by_factor_settings_recursive(settings, factor_settings, settings["depth"])

    # reduce as many cacluation odds as possible when operating for the first time
    # count NEW & REV oppty numbers

    @classmethod
    def opt_by_factor_settings_recursive(cls, settings: dict, factor_settings: dict,
                                         depth: int, optimized: dict = None):
        if depth == 0:
            return optimized

        logging.info("\n<<<< Now in [ISO] depth: %d >>>>" % depth)

        # init seq
        flattened_items = cls.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            item["seq"] = super().generate_seq(item["start"], item["end"], item["step"])

        # execute tests with seq
        result = cls.test_trade_result_in_seq(settings, factor_settings)
        # get opt
        cur_optimized = ISOAnalyzer.get_opt_initial_setting(result)

        # compare prev optimized with cur optimized, get opt
        if (optimized is None) or (cur_optimized["krw_earned"] > optimized["krw_earned"]):
            optimized = cur_optimized
        logging.info(optimized)

        # reset start, end, step
        division = settings["division"]
        factor_settings = cls.get_new_factor_settings(optimized["initial_setting"], factor_settings, division)

        depth -= 1
        return cls.opt_by_factor_settings_recursive(settings, factor_settings, depth, optimized)

    @staticmethod
    def flatten_factor_settings_items(factor_settings: dict):
        result = []
        for key in factor_settings.keys():
            item = factor_settings[key]
            # 2 depth items
            if key in ["new", "rev"]:
                for sub_item in item.values():
                    result.append(sub_item)
            # 1 depth items
            else:
                result.append(item)
        return result

    @classmethod
    def test_trade_result_in_seq(cls, settings: dict, factor_settings: dict):
        result = []

        # calculate total odds
        total_odds = 1
        flattened_items = cls.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            total_odds *= len(item["seq"])

        # create initial settings
        batch = cls.create_batch_initial_settings(factor_settings)

        # query data
        mm1_cursor, mm2_cursor = cls.get_history_data(settings)

        for index, item in enumerate(batch):
            logging.info("Now conducting [ISO] %d out of %d" % (index + 1, total_odds))
            # in ISO, init_factor_setting is subject to change and balance_setting is fixed
            bot = super().create_bot(settings["mm1"], settings["mm2"], settings["target_currency"],
                                     is_using_taker_fee=True)
            bot.run(mm1_cursor.clone(), mm2_cursor.clone(), item, True)
            combined_dict = cls.combine_initial_settings_in_dict(settings, item, bot)
            result.append(combined_dict)

        return result

    @staticmethod
    def get_new_factor_settings_item(current_opt, factor_item: dict, division: int):
        prev_start = factor_item["start"]
        prev_end = factor_item["end"]
        if prev_start >= prev_end:
            return factor_item

        prev_step = factor_item["step"]
        clone = copy.deepcopy(factor_item)
        clone["start"] = current_opt - prev_step
        if clone["start"] < 0:
            clone["start"] = 0
        clone["end"] = current_opt + prev_step
        clone["step"] = (clone["end"] - clone["start"]) / division
        return clone

    @classmethod
    def get_new_factor_settings(cls, opt_inital_settings: dict, factor_settings: dict, division: int):
        opt = opt_inital_settings
        pre = factor_settings
        clone = copy.deepcopy(factor_settings)

        clone["max_trading_coin"] = cls.get_new_factor_settings_item(opt["max_trading_coin"],
                                                                         pre["max_trading_coin"], division)
        for key in ["new", "rev"]:
            clone[key]["threshold"] = cls.get_new_factor_settings_item(
                opt[key]["threshold"],
                pre[key]["threshold"],
                division
            )
        return clone

    @staticmethod
    def create_batch_initial_settings(factor_settings: dict):
        result = []
        for rev_th in factor_settings["rev"]["threshold"]["seq"]:
            for new_th in factor_settings["new"]["threshold"]["seq"]:
                for max_unit in factor_settings["max_trading_coin"]["seq"]:
                    result.append({
                        "max_trading_coin": max_unit,
                        "new": {
                            "threshold": new_th
                        },
                        "rev": {
                            "threshold": rev_th
                        }
                    })
        return result

    @classmethod
    def combine_initial_settings_in_dict(cls, settings: dict, inital_settings: dict, bot: RfabBacktester):
        combined_dict = dict()
        krw_earned = bot.total_krw_bal - (settings["mm1"]["krw_balance"] + settings["mm2"]["krw_balance"])
        combined_dict["krw_earned"] = krw_earned
        combined_dict["new_num"] = bot.trade_new
        combined_dict["rev_num"] = bot.trade_rev
        combined_dict["initial_setting"] = inital_settings
        return combined_dict
