import logging
from trader.market.order import Market
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from optimizer.initial_setting_optimizer import InitialSettingOptimizer
from backtester.rfab_backtest import RfabBacktester

Global.configure_default_root_logging(log_level=logging.CRITICAL, should_log_to_file=False)

# choose which Coin Exchanger to use
# SharedMongoClient.KORBIT_DB_NAME = "korbit"
SharedMongoClient.COINONE_DB_NAME = "coinone"
SharedMongoClient.GOPAX_DB_NAME = "gopax"
SharedMongoClient.initialize(should_use_localhost_db=True)

start_time = Global.convert_local_datetime_to_epoch("2018.06.11 13:20:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.06.11 13:25:00", timezone="kr")

target_currency = "bch"

mm1_dict = {
    "mkt_tag": Market.VIRTUAL_CO,
    "market_fee": 0.001,
    "krw_balance": 5000000,
    "coin_balance": 0.5
}

mm2_dict = {
    "mkt_tag": Market.VIRTUAL_GP,
    "market_fee": 0.00075,
    "krw_balance": 500000,
    "coin_balance": 5
}

initial_setting_dict = {
    "max_trading_coin": 0.01,
    "min_trading_coin": 0,
    "max_ob_index_num": 1,
    "new_threshold": 50,
    "rev_threshold": 50,
    "new_factor": 1,
    "rev_factor": 1
}

trading_bot = RfabBacktester(mm1_dict, mm2_dict, initial_setting_dict, start_time, end_time, is_init_setting_opt=True)

initial_factor = {
    "MAX_COIN_TRADING_UNIT": {
        "start": 0,
        "end": 0.1
    },
    "NEW_SPREAD_THRESHOLD": {
        "start": 0,
        "end": 1000
    },
    "REV_SPREAD_THRESHOLD": {
        "start": 0,
        "end": 1000
    },
    "NEW_FACTOR": {
        "start": 1,
        "end": 3
    },
    "REV_FACTOR": {
        "start": 1,
        "end": 3
    }
}

optimized = InitialSettingOptimizer(trading_bot, initial_factor, division=4, depth=10).run()
print(optimized)
