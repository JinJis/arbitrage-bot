import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.risk_free_arb_bot import RiskFreeArbBot1, RiskFreeArbBot2

""" Gopax DB: avail from 2018.04.29 02:00"""

Global.configure_default_root_logging(should_log_to_file=True, log_level=logging.WARNING)
SharedMongoClient.initialize(should_use_localhost_db=False)
start_time = Global.convert_local_datetime_to_epoch("2018.05.31 22:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.06.01 01:00:00", timezone="kr")
# StatArbBot(should_db_logging=False, is_backtesting=True, start_time=start_time, end_time=end_time).run()
# RiskFreeArbBot1(target_currency="bch", should_db_logging=False, is_backtesting=True,
#                 start_time=start_time, end_time=end_time).run()
RiskFreeArbBot2(target_currency="bch", should_db_logging=False, is_backtesting=True,
                start_time=start_time, end_time=end_time).run()
