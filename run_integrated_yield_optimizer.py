from config.global_conf import Global
from trader.market.market import Market
from config.shared_mongo_client import SharedMongoClient
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer

Global.configure_default_root_logging(should_log_to_file=False)
SharedMongoClient.initialize(should_use_localhost_db=True)
start_time = Global.convert_local_datetime_to_epoch("2018.07.21 09:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.07.22 09:00:00", timezone="kr")

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
SharedMongoClient.instance()["db_name"]["col_name"].insert_many(iyo_result)
print(iyo_result)
