from config.global_conf import Global
from trader.market.market import Market
from config.shared_mongo_client import SharedMongoClient
from optimizer.initial_setting_optimizer import InitialSettingOptimizer

Global.configure_default_root_logging(should_log_to_file=True)
SharedMongoClient.initialize(should_use_localhost_db=True)

factor_settings = {
    "max_trading_coin": {
        "start": 0,
        "end": 0.1,
        "step_limit": 0.0001
    },
    "min_trading_coin": {
        "start": 0,
        "end": 0,
        "step_limit": 0
    },
    "new": {
        "threshold": {
            "start": 0,
            "end": 1000,
            "step_limit": 1

        },
        "factor": {
            "start": 1,
            "end": 3,
            "step_limit": 0.01
        }
    },
    "rev": {
        "threshold": {
            "start": 0,
            "end": 1000,
            "step_limit": 1
        },
        "factor": {
            "start": 1,
            "end": 3,
            "step_limit": 0.01
        }
    }
}

opt = InitialSettingOptimizer().run({
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
    "division": 4,
    "depth": 5,
    "start_time": "2018.06.24 12:25:00",
    "end_time": "2018.06.24 12:35:00"
}, factor_settings)
print(opt)
