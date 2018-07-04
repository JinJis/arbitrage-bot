import logging
from trader.market.market import Market
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from collector.oppty_time_collector import OpptyTimeCollector
from optimizer.initial_setting_optimizer import InitialSettingOptimizer
from optimizer.initial_balance_optimizer import InitialBalanceOptimizer

"""" 
[ISO log level] 
Trading Execution -> INFO
Result Return -> CRITICAL

[IBO log level]
Trading Execution -> WARNING
Result Return -> CRITICAL
"""
Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
SharedMongoClient.initialize(should_use_localhost_db=True)

start_time = Global.convert_local_datetime_to_epoch("2018.07.04 05:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.07.04 20:00:00", timezone="kr")

target_currency = "bch"
mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 100000, 1, target_currency)
mm2 = VirtualMarketManager(Market.VIRTUAL_GP, 0.00075, 100000, 1, target_currency)
mm1_col = SharedMongoClient.get_target_col(Market.VIRTUAL_CO, target_currency)
mm2_col = SharedMongoClient.get_target_col(Market.VIRTUAL_GP, target_currency)
mm1_data_cursor, mm2_data_cursor = SharedMongoClient.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

result_dict = OpptyTimeCollector(target_currency, mm1, mm2).run(mm1_data_cursor, mm2_data_cursor)

logging.critical("Oppty time result: %s" % result_dict)

# get total duration time for each trade
total_dur_dict = OpptyTimeCollector.get_total_duration_time(result_dict)
for key in total_dur_dict.keys():
    logging.info("Total [%s] duration (hour): %.2f" % (key.upper(), (total_dur_dict[key] / 60 / 60)))

# loop through oppty times
db_result = []
for trade_type in result_dict.keys():
    for time in result_dict[trade_type]:
        # Settings for ISO
        settings = {
            "target_currency": "bch",
            "mm1": {
                "market_tag": Market.VIRTUAL_CO,
                "fee_rate": 0.001,
                "krw_balance": 5000000,
                "coin_balance": 0.5
            },
            "mm2": {
                "market_tag": Market.VIRTUAL_GP,
                "fee_rate": 0.00075,
                "krw_balance": 500000,
                "coin_balance": 5

            },
            "division": 3,
            "depth": 3,
            "start_time": time[0],
            "end_time": time[1]
        }

        factor_settings = {
            "max_trading_coin": {"start": 0, "end": 0.05, "step_limit": 0.0001},
            "min_trading_coin": {"start": 0, "end": 0, "step_limit": 0},
            "new": {
                "threshold": {"start": 0, "end": 1000, "step_limit": 1},
                "factor": {"start": 1, "end": 3, "step_limit": 0.01}
            },
            "rev": {
                "threshold": {"start": 0, "end": 1000, "step_limit": 1},
                "factor": {"start": 1, "end": 3, "step_limit": 0.01}
            }
        }

        # FIXME: krw와 coin 상대 가격 현시세로 맞춰서 돌리기 !!!
        bal_factor_settings = {
            "mm1": {
                "krw_balance": {"start": 0, "end": 10000000, "step_limit": 10000
                                },
                "coin_balance": {"start": 0, "end": 10, "step_limit": 0.1
                                 }
            },
            "mm2": {
                "krw_balance": {"start": 0, "end": 10000000, "step_limit": 10000
                                },
                "coin_balance": {"start": 0, "end": 10, "step_limit": 0.1
                                 }
            }
        }
        logging.critical("Now in: [%s] start_time: %d, end_time: %d" % (trade_type.upper(), time[0], time[1]))

        """"RUN [ISO] Only (Initial Setting Optimizer)"""
        # InitialSettingOptimizer().run(settings, factor_settings)

        """"RUN [IBO-ISO] Total Solution (Initial Balance Optimizer)"""
        opt_ibo_info = InitialBalanceOptimizer.run(settings, bal_factor_settings)  # <-- Fix Factor setting in Class
        opt_ibo_info["oppty_time"] = time
        """
            opt_ibo_info = {
                "krw_earned": float,
                "total_krw_invested: float,
                "yield" : float,
                "factor_settings": dict, 
                "new_num": int, 
                "rev_num": int, 
                "balance_setting": dict}
                "oppty_time": list(start_time, end_time)
        """
        db_result.append(opt_ibo_info)

logging.critical("Final result to DB: %s" % db_result)
