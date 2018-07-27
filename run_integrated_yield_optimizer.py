import logging
import time
from config.global_conf import Global
from trader.market.market import Market
from config.shared_mongo_client import SharedMongoClient
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


def main():
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    time_list = ["2018.04.30 00:15:00", "2018.04.30 06:00:00", "2018.05.04 00:00:00", "2018.05.06 00:00:00",
                 "2018.05.08 00:00:00", "2018.05.10 00:00:00", "2018.05.12 00:00:00", "2018.05.14 00:00:00",
                 "2018.05.16 00:00:00", "2018.05.18 00:00:00", "2018.05.20 00:00:00", "2018.05.22 00:00:00",
                 "2018.05.24 00:00:00", "2018.05.26 00:00:00", "2018.05.28 00:00:00", "2018.05.30 00:00:00",
                 "2018.06.01 00:00:00", "2018.06.03 00:00:00", "2018.06.05 00:00:00", "2018.06.07 00:00:00",
                 "2018.06.09 00:00:00", "2018.06.11 00:00:00", "2018.06.13 00:00:00", "2018.06.15 00:00:00",
                 "2018.06.17 00:00:00", "2018.06.19 00:00:00", "2018.06.21 00:00:00", "2018.06.23 00:00:00",
                 "2018.06.25 00:00:00", "2018.06.27 00:00:00", "2018.06.29 00:00:00"]

    prev_time = None
    for cur_time in time_list:
        if prev_time is None:
            prev_time = cur_time
            continue
        logging.critical("Nohup conducting -> start_time: %s, end_time: %s" % (prev_time, cur_time))
        start_time = Global.convert_local_datetime_to_epoch(prev_time, timezone="kr")
        end_time = Global.convert_local_datetime_to_epoch(cur_time, timezone="kr")

        settings = {
            "target_currency": "bch",
            "mm1": {
                "market_tag": Market.VIRTUAL_CO,
                "fee_rate": 0.001,
                "krw_balance": 1000000,
                "coin_balance": 10
            },
            "mm2": {
                "market_tag": Market.VIRTUAL_GP,
                "fee_rate": 0.00075,
                "krw_balance": 1000000,
                "coin_balance": 10

            },
            "division": 3,
            "depth": 4,
            "consecution_time": 45,
            "start_time": start_time,
            "end_time": end_time
        }

        bal_factor_settings = {
            "mm1": {
                "krw_balance": {"start": 0, "end": 20000000, "step_limit": 10000
                                },
                "coin_balance": {"start": 0, "end": 20, "step_limit": 0.1
                                 }
            },
            "mm2": {
                "krw_balance": {"start": 0, "end": 20000000, "step_limit": 10000
                                },
                "coin_balance": {"start": 0, "end": 20, "step_limit": 0.1
                                 }
            }
        }

        factor_settings = {
            "max_trading_coin": {"start": 0, "end": 0.5, "step_limit": 0.0001},
            "min_trading_coin": {"start": 0, "end": 0, "step_limit": 0},
            "new": {
                "threshold": {"start": 0, "end": 2000, "step_limit": 1},
                "factor": {"start": 1, "end": 3, "step_limit": 0.01}
            },
            "rev": {
                "threshold": {"start": 0, "end": 2000, "step_limit": 1},
                "factor": {"start": 1, "end": 3, "step_limit": 0.01}
            }
        }

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
                    "balance_setting": dict
                }
        """
        # stat analysis and append to db result
        # SharedMongoClient.instance()["statistics"]["iyo_result"].insert_many(iyo_result)
        print(iyo_result)
        logging.critical("Nohup done, now conducting next time set!!")
        prev_time = cur_time
        time.sleep(180)


if __name__ == '__main__':
    main()
