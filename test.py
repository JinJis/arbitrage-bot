from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.stat_arb_bot import StatArbBot

Global.configure_default_root_logging()
SharedMongoClient.COINONE_DB_NAME = "coinone_180402"
SharedMongoClient.KORBIT_DB_NAME = "korbit_180402"
start_time = Global.convert_local_datetime_to_epoch("2018.03.28 10:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.03.30 10:00:00", timezone="kr")
StatArbBot(is_backtesting=True, start_time=start_time, end_time=end_time)
