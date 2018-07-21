import logging
from analyzer.analyzer import IBOAnalyzer
from optimizer.base_optimizer import BaseOptimizer
from collector.oppty_time_collector import OpptyTimeCollector
from optimizer.initial_setting_optimizer import InitialSettingOptimizer
from optimizer.initial_balance_optimizer import InitialBalanceOptimizer
from backtester.risk_free_arb_backtester import RfabBacktester

OTC = OpptyTimeCollector
ISO = InitialSettingOptimizer
IBO = InitialBalanceOptimizer


class IntegratedYieldOptimizer(BaseOptimizer):
    # default variables
    def_init_setting_dict = {
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
        oppty_dur_dict = OpptyTimeCollector.run(settings)
        logging.warning("Total Oppty Duration Dict: %s" % oppty_dur_dict)

        # get total duration hour for each trade
        total_dur_hour = OTC.get_total_duration_time(oppty_dur_dict)
        for key in total_dur_hour.keys():
            logging.warning("Total [%s] duration (hour): %.2f" % (key.upper(), (total_dur_hour[key] / 60 / 60)))

        # loop through oppty times
        db_result = []
        for trade_type in oppty_dur_dict.keys():
            if trade_type == "new":
                continue  # fixme
            for time in oppty_dur_dict[trade_type]:
                # apply each oppty duration
                settings["start_time"] = time[0]
                settings["end_time"] = time[1]
                logging.critical("Now in: [%s] start_time: %d, end_time: %d" % (trade_type.upper(), time[0], time[1]))

                # initial dry run
                bal_factor_settings, factor_settings = cls.opt_bal_init_settings_by_oppty(settings,
                                                                                          bal_factor_settings,
                                                                                          factor_settings)
                # create coin balance proportionate current exchange rate
                bal_factor_settings = IBO.create_coin_bal_from_krw_bal_by_exchange_rate(settings, bal_factor_settings)

                # create init step for balance settings and initial settings
                cls.create_init_step_for_bal_and_init_settings(settings, bal_factor_settings, factor_settings)

                # run recursive
                iyo_opt_result = cls.opt_by_bal_and_init_settings_recursive(settings, bal_factor_settings,
                                                                            factor_settings, settings["depth"])
                db_result.append(iyo_opt_result)
        return db_result

    @classmethod
    def opt_bal_init_settings_by_oppty(cls, settings: dict, bal_factor_settings: dict, factor_settings: dict):
        # opt initial settings by oppty
        factor_settings = cls.opt_factor_settings_by_oppty(settings, factor_settings, cls.def_init_setting_dict)
        # opt balance_settings by oppty
        bal_factor_settings = cls.opt_balance_settings_by_oppty(settings, bal_factor_settings,
                                                                cls.def_init_setting_dict)
        return bal_factor_settings, factor_settings

    @classmethod
    def create_init_step_for_bal_and_init_settings(cls, settings: dict, bal_factor_settings: dict,
                                                   factor_settings: dict):
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
                "new_num": int, 
                "rev_num": int, 
                "balance_setting": dict,
                "initial_setting": dict}
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
        for bal_item in bal_setting_batch:
            for init_setting_item in initial_settings_batch:

                iyo_index += 1
                logging.warning("Now conducting [IYO] %d out of %d" % (iyo_index, iyo_total_odds))

                # if total invested krw is 0, skip ISO (no trade anyway)
                if (bal_item["mm1"]["krw_balance"] + bal_item["mm2"]["krw_balance"]) == 0:
                    logging.warning("Skipped [IYO] because total invested KRW was 0!")
                    continue

                # If not invested krw is 0
                # sync batch with settings to loop over
                synced_settings = IBO.sync_batch_with_setting(settings, bal_item)

                # query data
                mm1_cursor, mm2_cursor = cls.get_history_data(synced_settings)
                bot = super().create_bot(synced_settings["mm1"], synced_settings["mm2"],
                                         synced_settings["target_currency"])
                bot.run(mm1_cursor.clone(), mm2_cursor.clone(), init_setting_item, True)

                # combine opted_inital_settings and bal_settings into formatted dict
                combined_dict = cls.combine_balance_and_init_settings_in_dict(bal_item, init_setting_item, bot)
                result.append(combined_dict)

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
    def combine_balance_and_init_settings_in_dict(cls, bal_settings: dict, init_settings: dict, bot: RfabBacktester):
        combined_dict = dict()
        combined_dict["total_krw_invested"] = bal_settings["mm1"]["krw_balance"] + bal_settings["mm2"]["krw_balance"]
        combined_dict["krw_earned"] = bot.total_krw_bal - combined_dict["total_krw_invested"]
        combined_dict["yield"] = combined_dict["krw_earned"] / combined_dict["total_krw_invested"] * 100
        combined_dict["new_num"] = bot.trade_new
        combined_dict["rev_num"] = bot.trade_rev
        combined_dict["balance_setting"] = bal_settings
        combined_dict["initial_setting"] = init_settings
        return combined_dict
