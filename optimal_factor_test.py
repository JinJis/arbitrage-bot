from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.stat_arb_bot import StatArbBot
import logging

Global.configure_default_root_logging(log_level=logging.CRITICAL, should_log_to_file=True)
# SharedMongoClient.COINONE_DB_NAME = "coinone_180402"
# SharedMongoClient.KORBIT_DB_NAME = "korbit_180402"
SharedMongoClient.KORBIT_DB_NAME = "korbit"
SharedMongoClient.COINONE_DB_NAME = "coinone"
SharedMongoClient.initialize(should_use_localhost_db=False)
# start_time = Global.convert_local_datetime_to_epoch("2018.03.25 00:00:00", timezone="kr")
# end_time = Global.convert_local_datetime_to_epoch("2018.03.30 00:00:00", timezone="kr")
start_time = Global.convert_local_datetime_to_epoch("2018.04.06 10:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.04.06 22:00:00", timezone="kr")

COIN_UNIT = (0.1,)
TARGET_SPREAD_STACK_HOUR = (18, 21, 24, 27)
Z_SCORE_SIGMA_PROB = (0.9,)

for coin_unit in COIN_UNIT:
    for stack_hour in TARGET_SPREAD_STACK_HOUR:
        for z_prob in Z_SCORE_SIGMA_PROB:
            logging.critical("------------------------------------------------------")
            logging.critical("coin unit: %.2f, stack_hour: %d, z_score: %d%%" % (coin_unit, stack_hour, z_prob * 100))
            StatArbBot.COIN_TRADING_UNIT = coin_unit
            StatArbBot.TARGET_SPREAD_STACK_HOUR = stack_hour
            StatArbBot.Z_SCORE_SIGMA = Global.get_z_score_for_probability(z_prob)
            StatArbBot(should_db_logging=False, is_backtesting=True, start_time=start_time, end_time=end_time).run()
