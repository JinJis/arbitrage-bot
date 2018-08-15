import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.arbitrage_combination_optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


def main(coin_name: str, mm1: str, mm2: str):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=True)

    time_list = ["2018.08.13 00:00:00", "2018.08.14 00:00:00"]

    prev_time = None
    for cur_time in time_list:
        if prev_time is None:
            prev_time = cur_time
            continue
        logging.warning("Nohup conducting -> start_time: %s, end_time: %s" % (prev_time, cur_time))
        start_time = Global.convert_local_datetime_to_epoch(prev_time, timezone="kr")
        end_time = Global.convert_local_datetime_to_epoch(cur_time, timezone="kr")

        # draw iyo_config for bal & factor_setting
        iyo_config = Global.read_iyo_setting_config(coin_name)

        # set settings, bal_fact_settings, factor_settings
        settings = TradeSettingConfig.get_settings(mm1=mm1,
                                                   mm2=mm2,
                                                   target_currency=coin_name,
                                                   start_time=start_time, end_time=end_time,
                                                   division=iyo_config["division"],
                                                   depth=iyo_config["depth"],
                                                   consecution_time=iyo_config["consecution_time"],
                                                   is_virtual_mm=True)

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(iyo_config["krw_seq_end"])

        factor_settings = TradeSettingConfig.get_factor_settings(iyo_config["max_trade_coin_end"],
                                                                 iyo_config["threshold_end"],
                                                                 iyo_config["factor_end"],
                                                                 iyo_config["appx_unit_coin_price"])

        iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings)
        """
            <data in IYO_result structure>
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
                    "balance_setting": dict,
                    "new_oppty_count": int,
                    "rev_oppty_count": int
                }
        """
        # stat analysis and append to db result
        print(iyo_result)
        logging.warning("Nohup done, now conducting next time set!!")
        prev_time = cur_time


if __name__ == '__main__':
    main(coin_name="bch", mm1="coinone", mm2="gopax")
