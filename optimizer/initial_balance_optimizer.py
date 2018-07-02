import logging
from analyzer.analyzer import ISOAnalyzer
from analyzer.analyzer import IBOAnalyzer
from optimizer.initial_setting_optimizer import InitialSettingOptimizer


class InitialBalanceOptimizer(InitialSettingOptimizer):
    factor_settings = {
        "max_trading_coin": {"start": 0, "end": 0.1, "step_limit": 0.0001},
        "min_trading_coin": {"start": 0, "end": 0, "step_limit": 0},
        "new": {
            "threshold": {"start": 0, "end": 1500, "step_limit": 1},
            "factor": {"start": 1, "end": 3, "step_limit": 0.01}
        },
        "rev": {
            "threshold": {"start": 0, "end": 1500, "step_limit": 1},
            "factor": {"start": 1, "end": 3, "step_limit": 0.01}
        }
    }

    @classmethod
    def run(cls, settings: dict, balance_settings: dict):

        # intial dry run
        logging.info("Now optimizing balance settings by oppty!!")
        balance_settings = cls.opt_balance_settings_by_oppty(settings, balance_settings)

        # set initial step for balance settings
        for market in balance_settings.keys():
            for item in balance_settings[market]:
                target_dict = balance_settings[market][item]
                target_dict["step"] = super().calc_steps_under_limit(target_dict, settings["division"])

        # run recursive
        return cls.opt_by_balance_settings_recursive(settings, balance_settings, settings["depth"])

    @classmethod
    def opt_balance_settings_by_oppty(cls, settings: dict, balance_settings: dict):
        # init bot and run
        bot = super().create_bot(settings["mm1"], settings["mm2"], settings["target_currency"])
        mm1_cursor, mm2_cursor = super().get_history_data(settings)
        bot.run(mm1_cursor, mm2_cursor, super().default_init_setting_dict, True)

        # get oppty count and log
        new_oppty_count = bot.trade_logger.new_oppty_counter
        rev_oppty_count = bot.trade_logger.rev_oppty_counter
        logging.info("[Result] NEW: %d, REV: %d" % (new_oppty_count, rev_oppty_count))

        # classify the kind of strategies and renew balance_settings accordingly
        clone = dict(balance_settings)
        mm1_krw_dict = clone["mm1"]["krw_balance"]
        mm1_coin_dict = clone["mm1"]["coin_balance"]
        mm2_krw_dict = clone["mm2"]["krw_balance"]
        mm2_coin_dict = clone["mm2"]["coin_balance"]

        if rev_oppty_count == 0:
            super().tie_end_start(mm1_coin_dict)
            super().tie_end_start(mm2_krw_dict)

        if new_oppty_count == 0:
            super().tie_end_start(mm1_krw_dict)
            super().tie_end_start(mm2_coin_dict)

        return clone

    @classmethod
    def opt_by_balance_settings_recursive(cls, settings: dict, balance_settings: dict, depth: int,
                                          optimized: list = None):
        if depth == 0:
            return optimized

        logging.critical("\n<<<< Now in [IBO] depth: %d >>>>" % depth)

        # init seq
        for market in balance_settings.keys():
            for item in balance_settings[market]:
                target_dict = balance_settings[market][item]
                target_dict["seq"] = super().generate_seq(target_dict["start"], target_dict["end"], target_dict["step"])

        # execute tests with seq
        result = cls.test_trade_result_in_seq(settings, balance_settings)

        # get opt
        # result = [krw_bal_after, factor_Settings, new # , rev #, balance_setting]
        cur_optimized = ISOAnalyzer.get_opt_initial_setting(result)

        # compare optimized in depth with cur optimized, get opt
        cur_optimized_yield = IBOAnalyzer.calc_krw_yield_in_percent(cur_optimized)

        if optimized is None:
            optimized = cur_optimized

        elif cur_optimized_yield > IBOAnalyzer.calc_krw_yield_in_percent(optimized):
            optimized = cur_optimized
            logging.info(optimized[4])

        # reset start, end, step
        division = settings["division"]
        balance_settings = cls.get_new_balance_settings(optimized[4], balance_settings, division)

        depth -= 1
        return cls.opt_by_balance_settings_recursive(settings, balance_settings, depth, optimized)

    @classmethod
    def test_trade_result_in_seq(cls, settings: dict, balance_setting: dict):
        result = []
        # calc total odds
        total_odds = 1
        for market in balance_setting.keys():
            for item in balance_setting[market]:
                target_dict = balance_setting[market][item]
                total_odds *= len(target_dict["seq"])

        # create balance settings batch
        bal_setting_batch = cls.create_balance_batch_with_seq(balance_setting)

        index = 0
        for item in bal_setting_batch:
            index += 1
            logging.info("Now conducting [IBO] %d out of %d" % (index, total_odds))

            # if total invested krw is 0, skip
            if (item["mm1"]["krw_balance"] + item["mm2"]["krw_balance"]) == 0:
                logging.info("ISO skipped becase total invested KRW is 0!")
                # fixme: 이 경우에는 빈 리스트 반환하는데 어케함 --> ISOAnalyzer의 get_opt_initial_setting 에러남
                continue

            # sync batch with settings to loop over
            synced_settings = cls.sync_batch_with_setting(settings, item)

            # opt_factor = [krw_bal_after, factor_Settings, new # , rev #]
            optimized_factor = InitialSettingOptimizer().run(synced_settings, cls.factor_settings)
            optimized_factor.append(item)

            # result = [krw_bal_after, factor_Settings, new # , rev #, balance_setting]
            result.append(optimized_factor)

        return result

    @classmethod
    def create_balance_batch_with_seq(cls, balance_settings: dict):
        result = []
        for mm1_krw in balance_settings["mm1"]["krw_balance"]["seq"]:
            for mm1_coin in balance_settings["mm1"]["coin_balance"]["seq"]:
                for mm2_krw in balance_settings["mm2"]["krw_balance"]["seq"]:
                    for mm2_coin in balance_settings["mm2"]["coin_balance"]["seq"]:
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
    def get_new_balance_settings(cls, opt_balance_settings: dict, balance_settings: dict, division: int):
        opt = opt_balance_settings
        pre = balance_settings
        clone = dict(balance_settings)

        for market in balance_settings.keys():
            for key in balance_settings[market]:
                clone[market][key] = cls.get_new_factor_settings_item(opt[market][key], pre[market][key], division)

        return clone

    @staticmethod
    def sync_batch_with_setting(settings: dict, batch: list):
        clone = dict(settings.copy())
        for market in batch:
            for item in batch[market]:
                clone[market][item] = batch[market][item]
        return clone
