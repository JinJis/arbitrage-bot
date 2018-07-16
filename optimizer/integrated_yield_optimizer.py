import logging
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from collector.oppty_time_collector import OpptyTimeCollector
from backtester.risk_free_arb_backtester import RfabBacktester
from optimizer.base_optimizer import BaseOptimizer
from analyzer.analyzer import IYOAnalyzer
from optimizer.initial_setting_optimizer import InitialSettingOptimizer
from optimizer.initial_balance_optimizer import InitialBalanceOptimizer

OTC = OpptyTimeCollector
ISO = InitialSettingOptimizer
IBO = InitialBalanceOptimizer


class IntegratedYieldOptimizer(BaseOptimizer):
    """
    <Algorithm Structure>
    A. run
        1. opt_balance_settings_by_oppty
            : check oppty and reset balance settings (ig. if only new, then no krw in mm2)

        2. set initial step for balance settings

        3. opt_by_balance_settings_recursive
            a. make sequence from bal_factors injected

            b. test_trade_result_in_seq     <-- returned result of 3.a
                1) create batch (all the possible odds from sequences)

                2) run ISO by looping through batch     <-- returned result of b.1)
                    - opted_factor, bal_settings, krw_earned, yield calculated
                    - gather all results from each one of loop to one list
                    - combine_factor_balance_settings_in_dict
                        : to unify with preset dictionary format for convenience and explicitness
                        --> return

            c. IBOAnalyzer.get_opt_yield_balance_setting    <-- returned result of b.2)
                - get the highest (or most attractive) yield item
                - append cur_opt to temp_result
            D. opt_by_balance_settings_recursive
                1) finally, return whole depthed optimized info dict

    """

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
        oppty_dur_dict = cls.get_oppty_time_dur_dict_by_otc(settings)

        # get total duration time for each trade
        total_dur_dict = OTC.get_total_duration_time(oppty_dur_dict)
        for key in total_dur_dict.keys():
            logging.warning("Total [%s] duration (hour): %.2f" % (key.upper(), (total_dur_dict[key] / 60 / 60)))

        # loop through oppty times
        db_result = []
        for trade_type in oppty_dur_dict.keys():
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

    @staticmethod
    def get_oppty_time_dur_dict_by_otc(settings: dict):
        target_currency = settings["target_currency"]
        mm1 = VirtualMarketManager(settings["mm1"]["market_tag"], settings["mm1"]["fee_rate"],
                                   settings["mm1"]["krw_balance"], settings["mm1"]["coin_balance"],
                                   target_currency)
        mm2 = VirtualMarketManager(settings["mm2"]["market_tag"], settings["mm2"]["fee_rate"],
                                   settings["mm2"]["krw_balance"], settings["mm2"]["coin_balance"],
                                   target_currency)
        mm1_col = SharedMongoClient.get_target_col(settings["mm1"]["market_tag"], target_currency)
        mm2_col = SharedMongoClient.get_target_col(settings["mm2"]["market_tag"], target_currency)
        mm1_data_cursor, mm2_data_cursor = \
            SharedMongoClient.get_data_from_db(mm1_col, mm2_col, settings["start_time"], settings["end_time"])
        oppty_dur_dict = OpptyTimeCollector(target_currency, mm1, mm2).run(mm1_data_cursor, mm2_data_cursor)
        return oppty_dur_dict

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
                "initial_setting": dict,
                "balance_setting": dict}
        """
        # get opt
        # optimize in terms of yield
        cur_optimized = IYOAnalyzer.get_opt_yield_balance_and_initial_setting(result)

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
        iyo_total_odds, ibo_total_odds, iso_total_odds = cls.calculate_each_total_odds(bal_factor_settings,
                                                                                       factor_settings)

        # create balance settings and inital settings batch
        bal_setting_batch = IBO.create_balance_batch_from_seq(bal_factor_settings)
        initial_settings_batch = ISO.create_batch_initial_settings(factor_settings)

        iyo_index = 0
        # loop through IBO first
        for ibo_index, bal_item in enumerate(bal_setting_batch):

            # if total invested krw is 0, skip ISO (no trade anyway)
            if (bal_item["mm1"]["krw_balance"] + bal_item["mm2"]["krw_balance"]) == 0:
                iyo_index += 1
                logging.warning("Now conducting [IYO] %d out of %d" % (iyo_index, iyo_total_odds))
                logging.warning("Skipped because total invested KRW is 0!")
                continue

            # loop thorugh ISO secondly
            for iso_index, init_setting_item in enumerate(initial_settings_batch):
                iyo_index += 1
                logging.warning("Now conducting [IYO] %d out of %d / [IBO] %d out of %d / [ISO] %d out of %d" %
                                (iyo_index, iyo_total_odds, ibo_index, ibo_total_odds, iso_index, iso_total_odds))

                # sync batch with settings to loop over
                synced_settings = IBO.sync_batch_with_setting(settings, bal_item)

                # query data
                mm1_cursor, mm2_cursor = cls.get_history_data(synced_settings)

                # opt_factor = [krw_bal_after, factor_Settings, new # , rev #]
                bot = super().create_bot(synced_settings["mm1"], synced_settings["mm2"],
                                         synced_settings["target_currency"])
                bot.run(mm1_cursor.clone(), mm2_cursor.clone(), init_setting_item, True)
                # combine opted_inital_settings and bal_settings into formatted dict
                combined_dict = cls.combine_balance_and_init_settings_in_dict(bal_item, init_setting_item, bot)
                result.append(combined_dict)

        return result

    @classmethod
    def calculate_each_total_odds(cls, bal_factor_settings: dict, factor_settings: dict):
        ibo_total_odds = 1
        for market in bal_factor_settings.keys():
            sequence = bal_factor_settings[market]["krw_balance"]["seq"]
            ibo_total_odds *= len(sequence)
        iso_total_odds = 1
        flattened_items = ISO.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            iso_total_odds *= len(item["seq"])
        iyo_total_odds = ibo_total_odds * iso_total_odds
        return iyo_total_odds, ibo_total_odds, iso_total_odds

    @classmethod
    def combine_balance_and_init_settings_in_dict(cls, bal_settings: dict, init_settings: dict, bot: RfabBacktester):
        combined_dict = dict()
        combined_dict["total_krw_invested"] = bal_settings["mm1"]["krw_balance"] + bal_settings["mm2"]["krw_balance"]
        combined_dict["krw_earned"] = bot.total_krw_bal - combined_dict["total_krw_invested"]
        combined_dict["yield"] = combined_dict["krw_earned"] / combined_dict["total_krw_invested"] * 100
        combined_dict["new_num"] = bot.trade_new
        combined_dict["rev_num"] = bot.trade_rev
        combined_dict["initial_setting"] = init_settings
        combined_dict["balance_setting"] = bal_settings
        return combined_dict
