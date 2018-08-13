import logging
from config.global_conf import Global
from config.trade_setting_config import MarketSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.arbitrage_combination_optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


def main():
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=True)

    time_list = ["2018.07.13 07:00:00", "2018.07.13 15:00:00"]

    prev_time = None
    for cur_time in time_list:
        if prev_time is None:
            prev_time = cur_time
            continue
        logging.warning("Nohup conducting -> start_time: %s, end_time: %s" % (prev_time, cur_time))
        start_time = Global.convert_local_datetime_to_epoch(prev_time, timezone="kr")
        end_time = Global.convert_local_datetime_to_epoch(cur_time, timezone="kr")

        settings = MarketSettingConfig.get_settings(mm1="coinone",
                                                    mm2="gopax",
                                                    target_currency="bch",
                                                    start_time=start_time, end_time=end_time,
                                                    is_virtual_mm=True)

        bal_factor_settings = MarketSettingConfig.get_bal_fact_settings(krw_seq_end=10000000)

        factor_settings = MarketSettingConfig.get_factor_settings(max_trading_coin_end=0.1,
                                                                  threshold_end=2500,
                                                                  factor_end=3,
                                                                  appx_unit_coin_price=800000)

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
        # time.sleep(240)

    # Fixme: this is for Nonhup, if not erase
    # Global.send_to_slack_channel("[IYO] finished!! Check and nohup another time set!!")


if __name__ == '__main__':
    main()
