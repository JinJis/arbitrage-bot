import copy
import logging
from config.shared_mongo_client import SharedMongoClient
from analyzer.analyzer import BasicAnalyzer, IBOAnalyzer
from optimizer.base_optimizer import BaseOptimizer
from backtester.risk_free_arb_backtester import RfabBacktester


class InitialBalanceOptimizer(BaseOptimizer):

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
    def run(cls, settings: dict, bal_factor_settings: dict):

        # initial dry run
        logging.warning("Now optimizing balance settings by oppty!!")
        bal_factor_settings = super().opt_balance_settings_by_oppty(settings, bal_factor_settings,
                                                                    cls.default_initial_setting_dict)

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
        for item in ["start", "end", "step_limit"]:
            clone["mm1"]["coin_balance"][item] = round(clone["mm2"]["krw_balance"][item] / exchange_rate, 5)
            clone["mm2"]["coin_balance"][item] = round(clone["mm1"]["krw_balance"][item] / exchange_rate, 5)
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
                "balance_setting": dict}
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
        for item in bal_setting_batch:
            index += 1
            logging.warning("Now conducting [IBO] %d out of %d" % (index, total_odds))

            # if total invested krw is 0, skip (no trade anyway)
            if (item["mm1"]["krw_balance"] + item["mm2"]["krw_balance"]) == 0:
                logging.warning("ISO skipped because total invested KRW is 0!")
                continue

            # sync batch with settings to loop over
            synced_settings = cls.sync_batch_with_setting(settings, item)

            # query data
            mm1_cursor, mm2_cursor = cls.get_history_data(synced_settings)

            # opt_factor = [krw_bal_after, factor_Settings, new # , rev #]
            bot = super().create_bot(synced_settings["mm1"], synced_settings["mm2"], synced_settings["target_currency"])
            # in IBO, init_factor_setting is fixed and balance_setting is subject to change
            bot.run(mm1_cursor.clone(), mm2_cursor.clone(), cls.default_initial_setting_dict, True)
            # combine opted_factor_settings returned and bal_settings into dict
            combined_dict = cls.combine_balance_settings_in_dict(item, bot)
            result.append(combined_dict)

        return result

    @classmethod
    def get_new_balance_settings(cls, opt_balance_settings: dict, bal_factor_settings: dict, division: int):
        opt = opt_balance_settings
        pre = bal_factor_settings
        clone = copy.deepcopy(bal_factor_settings)

        for market in bal_factor_settings.keys():
            for key in bal_factor_settings[market]:
                clone[market][key] = super().get_new_factor_settings_item(opt[market][key], pre[market][key], division)
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

    @staticmethod
    def sync_batch_with_setting(settings: dict, batch: dict):
        clone = copy.deepcopy(settings)
        for market in batch.keys():
            for item in batch[market]:
                clone[market][item] = batch[market][item]
        return clone

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
