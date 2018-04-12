from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.stat_arb_bot import StatArbBot
from trader.risk_free_arb_bot import RiskFreeArbBot

Global.configure_default_root_logging(should_log_to_file=True)
SharedMongoClient.initialize(should_use_localhost_db=False)
start_time = Global.convert_local_datetime_to_epoch("2018.04.11 10:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.04.13 05:00:00", timezone="kr")
# StatArbBot(should_db_logging=False, is_backtesting=True, start_time=start_time, end_time=end_time).run()
RiskFreeArbBot(should_db_logging=False, is_backtesting=True, start_time=start_time, end_time=end_time).run()
