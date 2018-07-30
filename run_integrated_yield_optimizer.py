import logging
import time
from config.global_conf import Global
from trader.market.market import Market
from config.shared_mongo_client import SharedMongoClient
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


def main():
    Global.configure_default_root_logging(should_log_to_file=True, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=True)

    time_list = ["2018.06.30 18:00:00", "2018.07.01 00:00:00", "2018.07.03 00:00:00", "2018.07.05 00:00:00",
                 "2018.07.07 00:00:00", "2018.07.09 00:00:00", "2018.07.11 00:00:00", "2018.07.13 00:00:00",
                 "2018.07.15 00:00:00", "2018.07.17 00:00:00", "2018.07.19 00:00:00", "2018.07.21 00:00:00",
                 "2018.07.23 00:00:00", "2018.07.25 00:00:00", "2018.07.26 02:00:00"]

    prev_time = None
    for cur_time in time_list:
        if prev_time is None:
            prev_time = cur_time
            continue
        logging.warning("Nohup conducting -> start_time: %s, end_time: %s" % (prev_time, cur_time))
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
            "depth": 5,
            "consecution_time": 30,
            "start_time": start_time,
            "end_time": end_time
        }

        bal_factor_settings = {
            "mm1": {
                "krw_balance": {"start": 0, "end": 20000000, "step_limit": 1000
                                },
                "coin_balance": {"start": 0, "end": 20, "step_limit": 0.1
                                 }
            },
            "mm2": {
                "krw_balance": {"start": 0, "end": 20000000, "step_limit": 1000
                                },
                "coin_balance": {"start": 0, "end": 20, "step_limit": 0.1
                                 }
            }
        }

        factor_settings = {
            "max_trading_coin": {"start": 0, "end": 0.8, "step_limit": 0.0001},
            "min_trading_coin": {"start": 0, "end": 0, "step_limit": 0},
            "new": {
                "threshold": {"start": 0, "end": 2500, "step_limit": 1},
                "factor": {"start": 1, "end": 1, "step_limit": 0.01}
            },
            "rev": {
                "threshold": {"start": 0, "end": 2500, "step_limit": 1},
                "factor": {"start": 1, "end": 1, "step_limit": 0.01}
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
                    "balance_setting": dict,
                    "new_oppty_count": int,
                    "rev_oppty_count": int
                }
        """
        # stat analysis and append to db result
        SharedMongoClient.instance()["statistics"]["iyo_test"].insert_many(iyo_result)
        logging.warning("Nohup done, now conducting next time set!!")
        prev_time = cur_time
        time.sleep(120)

    # Fixme: this is for Nonhup, if not erase
    Global.send_to_slack_channel("[IYO] finished!! Check and nohup another time set!!")


if __name__ == '__main__':
    main()
