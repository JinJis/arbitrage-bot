import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from analyzer.iyo_analyzer import IYOMongoDBAnalyzer

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=True)

iyo_data = {
    "total_krw_invested": 1975308.64197531,
    "krw_earned": 212.508038024884,
    "yield": 0.0107582194250097,
    "new_traded": 245,
    "rev_traded": 0,
    "end_balance": {
        "mm1": {
            "krw": 1792592.54014531,
            "bch": 0.11648588751
        },
        "mm2": {
            "krw": 182928.609868025,
            "bch": 1.14238516432099
        }
    },
    "settings": {
        "target_currency": "bch",
        "mm1": {
            "market_tag": "Virtual_CO",
            "fee_rate": 0.001,
            "krw_balance": 1975308.64197531,
            "coin_balance": 0.0
        },
        "mm2": {
            "market_tag": "Virtual_GP",
            "fee_rate": 0.00075,
            "krw_balance": 0,
            "coin_balance": 1.25898765432099
        },
        "division": 3,
        "depth": 5,
        "consecution_time": 30,
        "start_time": 1525043162,
        "end_time": 1525044383
    },
    "initial_setting": {
        "max_trading_coin": 0.0790123456790123,
        "min_trading_coin": 0,
        "new": {
            "threshold": 0,
            "factor": 1
        },
        "rev": {
            "threshold": 0,
            "factor": 1
        }
    },
    "balance_setting": {
        "mm1": {
            "krw_balance": 1975308.64197531,
            "coin_balance": 0.0
        },
        "mm2": {
            "krw_balance": 0,
            "coin_balance": 1.25898765432099
        }
    },
    "new_oppty_count": 245,
    "rev_oppty_count": 0
}
result = IYOMongoDBAnalyzer().run(iyo_data=iyo_data)
print(result)
