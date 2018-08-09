from config.global_conf import Global
from trader.market.market import Market
from config.shared_mongo_client import SharedMongoClient
from optimizer.arbitrage_combination_optimizer.initial_setting_optimizer import InitialSettingOptimizer

Global.configure_default_root_logging(should_log_to_file=False)
SharedMongoClient.initialize(should_use_localhost_db=True)
start_time = Global.convert_local_datetime_to_epoch("2018.07.11 09:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.07.12 09:00:00", timezone="kr")

settings = {
    "target_currency": "bch",
    "mm1": {
        "market_tag": Market.VIRTUAL_CO,
        "fee_rate": 0.001,
        "krw_balance": 10000,
        "coin_balance": 0.1
    },
    "mm2": {
        "market_tag": Market.VIRTUAL_GP,
        "fee_rate": 0.00075,
        "krw_balance": 10000,
        "coin_balance": 0.1

    },
    "division": 3,
    "depth": 4,
    "consecution_time": 30,
    "start_time": start_time,
    "end_time": end_time
}

factor_settings = {
    "max_trading_coin": {"start": 0, "end": 0.1, "step_limit": 0.0001},
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

ISO_result = InitialSettingOptimizer().run(settings, factor_settings)
print(ISO_result)
