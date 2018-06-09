from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
import logging
from optimizer.initial_setting_optimizer import InitialSettingOptimizer
from trader.risk_free_arb_bot import RiskFreeArbBot2

Global.configure_default_root_logging(log_level=logging.CRITICAL, should_log_to_file=False)

# choose which Coin Exchanger to use
# SharedMongoClient.KORBIT_DB_NAME = "korbit"
SharedMongoClient.COINONE_DB_NAME = "coinone"
SharedMongoClient.GOPAX_DB_NAME = "gopax"

# Fixme wheter to use 'local_host' or not
SharedMongoClient.initialize(should_use_localhost_db=False)

start_time = Global.convert_local_datetime_to_epoch("2018.06.08 10:20:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.06.08 11:20:00", timezone="kr")

trading_bot = RiskFreeArbBot2(target_currency="bch", should_db_logging=False, is_backtesting=True,
                              is_init_setting_opt=True,
                              start_time=start_time, end_time=end_time)

initial_factor = {
    "MAX_COIN_TRADING_UNIT": {
        "start": 0.0005,
        "end": 0.05
    },
    "NEW_SPREAD_THRESHOLD": {
        "start": 0,
        "end": 1300
    },
    "REV_SPREAD_THRESHOLD": {
        "start": 0,
        "end": 1300
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

optimized = InitialSettingOptimizer(trading_bot, initial_factor, division=4, depth=5).run()
print(optimized)
