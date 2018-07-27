import logging
import copy
from analyzer.trade_analyzer import IBOAnalyzer
from optimizer.base_optimizer import BaseOptimizer
from collector.oppty_time_collector import OpptyTimeCollector
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
            "threshold": 0,
            "factor": 1
        },
        "rev": {
            "threshold": 0,
            "factor": 1
        }
    }

    @classmethod
    def run(cls, settings: dict, bal_factor_settings: dict, factor_settings: dict):

        # get oppty_time_duration dict
        oppty_dur_dict = OTC.run(settings)
        logging.warning("Total Oppty Duration Dict: %s" % oppty_dur_dict)

        # get total duration hour for each trade
        total_dur_hour = OTC.get_total_duration_time(oppty_dur_dict)
        for key in total_dur_hour.keys():
            logging.warning("Total [%s] duration (hour): %.2f" % (key.upper(), (total_dur_hour[key] / 60 / 60)))

        # loop through oppty times
        db_result = []
        for trade_type in oppty_dur_dict.keys():
            for time in oppty_dur_dict[trade_type]:
                try:
                    # clone settings, balance factor settings, factor settings with original one
                    settings_clone = copy.deepcopy(settings)
                    bal_fact_set_clone = copy.deepcopy(bal_factor_settings)
                    fact_set_clone = copy.deepcopy(factor_settings)

                    # apply each oppty duration
                    settings_clone["start_time"] = time[0]
                    settings_clone["end_time"] = time[1]
                    logging.critical(
                        "Now in: [%s] start_time: %d, end_time: %d" % (trade_type.upper(), time[0], time[1]))

                    # initial dry run -> get new, rev oppty count
                    new_oppty_count, rev_oppty_count = super().count_oppty_num(settings_clone,
                                                                               cls.default_initial_setting_dict)

                    # save total possible oppty count in settings
                    settings_clone["new_oppty_count"] = new_oppty_count
                    settings_clone["rev_oppty_count"] = rev_oppty_count

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
                    print(settings_clone["new_oppty_count"])
                    print(settings_clone["rev_oppty_count"])
                    print(iyo_opt_result["new_traded"])
                    print(iyo_opt_result["rev_traded"])
                    db_result.append(iyo_opt_result)
                except Exception as e:
                    logging.error("Something went wrong while executing IYO loop!", time, e)
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
            final_opt_yield = optimized["yield"]
            logging.critical("\n[IYO Final Opt Result]"
                             "\n>>>Final Opted Yield: %.4f%%"
                             "\n>>>Final Optimized Info: %s" % (final_opt_yield, optimized))
            return optimized

        logging.critical("\n<<<< Now in [IYO] depth: %d >>>>" % depth)

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
        """
            <data structure>
            1)  result = [combined_dict, combined_dict, combined_dict, ... ]
            2)  combined_dict or cur_optimized = {                  
                    "total_krw_invested: float,
                    "krw_earned": float,                
                    "yield" : float,
                    "new_traded": int, 
                    "rev_traded": int,
                    "end_balance": dict,
                    "settings": dict,
                    "initial_setting": dict,
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
        logging.critical("[IYO Depth:%d] Current Opted Yield: %.4f%%" % (depth, cur_optimized["yield"]))

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
                logging.warning("Now conducting [IYO] %d out of %d" % (iyo_index, iyo_total_odds))

                # if total invested krw is 0, skip ISO (no trade anyway)
                if (bal_setting["mm1"]["krw_balance"] + bal_setting["mm2"]["krw_balance"]) == 0:
                    logging.warning("Skipped [IYO] because total invested KRW was 0!")
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

        result["total_krw_invested"] = bal_setting["mm1"]["krw_balance"] + bal_setting["mm2"]["krw_balance"]
        result["krw_earned"] = exec_result["total_krw_bal"] - result["total_krw_invested"]
        result["yield"] = result["krw_earned"] / result["total_krw_invested"] * 100
        result["new_traded"] = exec_result["new_traded"]
        result["rev_traded"] = exec_result["rev_traded"]
        result["end_balance"] = exec_result["end_balance"]
        result["settings"] = cloned_settings
        result["initial_setting"] = init_setting
        result["balance_setting"] = bal_setting
        return result
