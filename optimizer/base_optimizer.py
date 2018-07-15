import copy
import logging
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from backtester.risk_free_arb_backtester import RfabBacktester


class BaseOptimizer:

    @classmethod
    def oppty_num_checker(cls, settings: dict, default_init_setting_dict: dict):
        bot = cls.create_bot(settings["mm1"], settings["mm2"], settings["target_currency"])
        mm1_cursor, mm2_cursor = cls.get_history_data(settings)
        bot.run(mm1_cursor, mm2_cursor, default_init_setting_dict, True)

        # get oppty count and log
        new_oppty_count = bot.trade_logger.new_oppty_counter
        rev_oppty_count = bot.trade_logger.rev_oppty_counter
        return new_oppty_count, rev_oppty_count

    @classmethod
    def opt_factor_settings_by_oppty(cls, settings: dict, factor_settings: dict,  default_init_setting_dict: dict):
        # init bot and run
        (new_oppty_count, rev_oppty_count) = cls.oppty_num_checker(settings, default_init_setting_dict)
        logging.info("Oppty Checked Successfully!! -- NEW oppty: %d, REV oppty: %d"
                     % (new_oppty_count, rev_oppty_count))

        # classify the kind of strategies and renew factor_settings accordingly
        clone = copy.deepcopy(factor_settings)
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

    @classmethod
    def opt_balance_settings_by_oppty(cls, settings: dict, bal_factor_settings: dict, default_init_setting_dict: dict):
        # init bot and run
        (new_oppty_count, rev_oppty_count) = cls.oppty_num_checker(settings, default_init_setting_dict)
        logging.warning("[Result] NEW: %d, REV: %d" % (new_oppty_count, rev_oppty_count))

        # if there is no oppty, stop bot
        if not new_oppty_count and not rev_oppty_count:
            raise Exception("No Oppty found. Please adjust time duration to get optimized!!")

        # classify the kind of strategies and renew bal_factor_settings accordingly
        clone = copy.deepcopy(bal_factor_settings)
        mm1_krw_dict = clone["mm1"]["krw_balance"]
        mm2_krw_dict = clone["mm2"]["krw_balance"]

        if rev_oppty_count == 0:
            cls.tie_end_start(mm2_krw_dict)

        if new_oppty_count == 0:
            cls.tie_end_start(mm1_krw_dict)

        return clone

    @staticmethod
    def calc_steps_under_limit(item: dict, division: int):
        step = (item["end"] - item["start"]) / division
        return max([step, item["step_limit"]])

    @classmethod
    def create_bot(cls, mm1_settings: dict, mm2_settings: dict, target_currency: str):
        mm1 = cls.create_market(mm1_settings, target_currency)
        mm2 = cls.create_market(mm2_settings, target_currency)
        return RfabBacktester(mm1, mm2, target_currency)

    @staticmethod
    def create_market(market_settings: dict, target_currency: str):
        return VirtualMarketManager(
            market_settings["market_tag"],
            market_settings["fee_rate"],
            market_settings["krw_balance"],
            market_settings["coin_balance"],
            target_currency
        )

    @staticmethod
    def get_history_data(settings: dict):
        target_currency = settings["target_currency"]
        mm1_col = SharedMongoClient.get_target_db(settings["mm1"]["market_tag"])[target_currency + "_orderbook"]
        mm2_col = SharedMongoClient.get_target_db(settings["mm2"]["market_tag"])[target_currency + "_orderbook"]
        return SharedMongoClient.get_data_from_db(mm1_col, mm2_col, settings["start_time"], settings["end_time"])

    @staticmethod
    def tie_end_start(target_dict: dict):
        target_dict["end"] = target_dict["start"]

    @staticmethod
    def generate_seq(start, end, step):
        result = []
        stepper = start
        while stepper < end:
            result.append(stepper)
            stepper += step
        result.append(end)
        return result

    @staticmethod
    def get_new_factor_settings_item(current_opt, factor_item: dict, division: int) -> dict:
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
