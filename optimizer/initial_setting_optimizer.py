import logging
from analyzer.analyzer import ISOAnalyzer
from backtester.risk_free_arb_backtest import RfabBacktester
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.virtual_market_manager import VirtualMarketManager


class InitialSettingOptimizer:
    default_init_setting_dict = {
        "max_trading_coin": 0.01,
        "min_trading_coin": 0,
        "new": {
            "threshold": 10,
            "factor": 1
        },
        "rev": {
            "threshold": 10,
            "factor": 1
        }
    }

    @staticmethod
    def get_history_data(settings: dict):
        target_currency = settings["target_currency"]
        start_time = Global.convert_local_datetime_to_epoch(settings["start_time"], timezone="kr")
        end_time = Global.convert_local_datetime_to_epoch(settings["end_time"], timezone="kr")
        mm1_col = SharedMongoClient.get_target_db(settings["mm1"]["market_tag"])[target_currency + "_orderbook"]
        mm2_col = SharedMongoClient.get_target_db(settings["mm2"]["market_tag"])[target_currency + "_orderbook"]
        return SharedMongoClient.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

    @staticmethod
    def create_market(market_settings: dict, target_currency: str):
        return VirtualMarketManager(
            market_settings["market_tag"],
            market_settings["fee_rate"],
            market_settings["krw_balance"],
            market_settings["coin_balance"],
            target_currency
        )

    @classmethod
    def create_bot(cls, mm1_settings: dict, mm2_settings: dict, target_currency: str):
        mm1 = cls.create_market(mm1_settings, target_currency)
        mm2 = cls.create_market(mm2_settings, target_currency)
        return RfabBacktester(mm1, mm2, target_currency)

    # reduce as many cacluation odds as possible when operating for the first time
    # count NEW & REV oppty numbers
    @classmethod
    def opt_factor_settings_by_oppty(cls, settings: dict, factor_settings: dict):
        # init bot and run
        bot = cls.create_bot(settings["mm1"], settings["mm2"], settings["target_currency"])
        mm1_cursor, mm2_cursor = cls.get_history_data(settings)
        bot.run(mm1_cursor, mm2_cursor, cls.default_init_setting_dict, True)

        # get oppty count and log
        new_oppty_count = bot.trade_logger.new_oppty_counter
        rev_oppty_count = bot.trade_logger.rev_oppty_counter
        logging.info("Oppty Checked Successfully!! -- NEW oppty: %d, REV oppty: %d"
                     % (new_oppty_count, rev_oppty_count))

        # classify the kind of strategies and renew factor_settings accordingly
        clone = dict(factor_settings)
        new_factor_dict = clone["new"]["factor"]
        rev_factor_dict = clone["rev"]["factor"]
        new_threshold_dict = clone["new"]["threshold"]
        rev_threshold_dict = clone["rev"]["threshold"]

        if rev_oppty_count == 0:
            cls.tie_end_start(rev_factor_dict)
            cls.tie_end_start(rev_threshold_dict)
            cls.tie_end_start(new_factor_dict)

        if new_oppty_count == 0:
            cls.tie_end_start(new_factor_dict)
            cls.tie_end_start(new_threshold_dict)
            cls.tie_end_start(rev_factor_dict)

        if new_oppty_count > rev_oppty_count:
            cls.tie_end_start(new_factor_dict)
        elif new_oppty_count < rev_oppty_count:
            cls.tie_end_start(rev_factor_dict)
        else:
            cls.tie_end_start(new_factor_dict)
            cls.tie_end_start(rev_factor_dict)

        return clone

    @staticmethod
    def tie_end_start(target_dict: dict):
        target_dict["end"] = target_dict["start"]

    @classmethod
    def run(cls, settings: dict, factor_settings: dict):
        # intial dry run
        factor_settings = cls.opt_factor_settings_by_oppty(settings, factor_settings)

        # set initial step
        flattened_items = cls.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            item["step"] = cls.calc_steps_under_limit(item, settings["division"])

        # run recursive
        return cls.opt_by_factor_settings_recursive(settings, factor_settings, settings["depth"])

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

    @staticmethod
    def calc_steps_under_limit(item: dict, division: int):
        step = (item["end"] - item["start"]) / division
        return max([step, item["step_limit"]])

    @staticmethod
    def generate_seq(start, end, step):
        result = []
        stepper = start
        while stepper < end:
            result.append(stepper)
            stepper += step
        result.append(end)
        return result

    @classmethod
    def opt_by_factor_settings_recursive(cls, settings: dict, factor_settings: dict,
                                         depth: int, optimized: list = None):
        if depth == 0:
            return optimized

        logging.info("\n<<<< Now in depth: %d >>>>" % depth)

        # init seq
        flattened_items = cls.flatten_factor_settings_items(factor_settings)
        for item in flattened_items:
            item["seq"] = cls.generate_seq(item["start"], item["end"], item["step"])

        # execute tests with seq
        result = cls.test_trade_result_in_seq(settings, factor_settings)
        # get opt
        cur_optimized = ISOAnalyzer.get_opt_initial_setting(result)

        # compare prev optimized with cur optimized, get opt
        if (optimized is None) or (cur_optimized[0] > optimized[0]):
            optimized = cur_optimized
        logging.info(optimized)

        # reset start, end, step
        division = settings["division"]
        factor_settings = cls.get_new_factor_settings(optimized[1], factor_settings, division)

        depth -= 1
        return cls.opt_by_factor_settings_recursive(settings, factor_settings, depth, optimized)

    @classmethod
    def get_new_factor_settings(cls, opt_inital_settings: dict, factor_settings: dict, division: int):
        opt = opt_inital_settings
        pre = factor_settings
        clone = dict(factor_settings)

        for key in ["max_trading_coin", "min_trading_coin"]:
            clone[key] = cls.get_new_factor_settings_item(opt[key], pre[key], division)
        for key_d1 in ["new", "rev"]:
            for key_d2 in ["factor", "threshold"]:
                clone[key_d1][key_d2] = cls.get_new_factor_settings_item(
                    opt[key_d1][key_d2],
                    pre[key_d1][key_d2],
                    division
                )
        return clone

    @staticmethod
    def get_new_factor_settings_item(current_opt, factor_settings_item: dict, division: int) -> dict:
        prev_start = factor_settings_item["start"]
        prev_end = factor_settings_item["end"]
        if prev_start >= prev_end:
            return factor_settings_item

        prev_step = factor_settings_item["step"]
        clone = dict(factor_settings_item)
        clone["start"] = current_opt - prev_step
        if clone["start"] < 0:
            clone["start"] = 0
        clone["end"] = current_opt + prev_step
        clone["step"] = (clone["end"] - clone["start"]) / division
        # TODO
        print(clone["step"])
        return clone

    @staticmethod
    def create_batch_initial_settings(factor_settings: dict):
        result = []
        for min_unit in factor_settings["min_trading_coin"]["seq"]:
            for new_f in factor_settings["new"]["factor"]["seq"]:
                for rev_f in factor_settings["rev"]["factor"]["seq"]:
                    for rev_th in factor_settings["rev"]["threshold"]["seq"]:
                        for new_th in factor_settings["new"]["threshold"]["seq"]:
                            for max_unit in factor_settings["max_trading_coin"]["seq"]:
                                result.append({
                                    "max_trading_coin": max_unit,
                                    "min_trading_coin": min_unit,
                                    "new": {
                                        "threshold": new_th,
                                        "factor": new_f
                                    },
                                    "rev": {
                                        "threshold": rev_th,
                                        "factor": rev_f
                                    }
                                })
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
            logging.info("Now conducting %d out of %d" % (index + 1, total_odds))
            bot = cls.create_bot(settings["mm1"], settings["mm2"], settings["target_currency"])
            bot.run(mm1_cursor.clone(), mm2_cursor.clone(), cls.default_init_setting_dict, True)
            result.append([bot.total_krw_bal, item, bot.trade_new, bot.trade_rev])

        return result
