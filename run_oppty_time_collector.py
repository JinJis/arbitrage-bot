import logging
from config.global_conf import Global
from trader.market.market import Market
from config.shared_mongo_client import SharedMongoClient
from collector.oppty_time_collector import OpptyTimeCollector

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
SharedMongoClient.initialize(should_use_localhost_db=False)

start_time = Global.convert_local_datetime_to_epoch("2018.08.12 00:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.08.12 18:40:00", timezone="kr")

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

result_dict = OpptyTimeCollector.run(settings)

logging.critical("Oppty time result: %s" % result_dict)

# get total duration time for each trade
total_dur_dict = OpptyTimeCollector.get_total_duration_time(result_dict)
for key in total_dur_dict.keys():
    logging.warning("Total [%s] duration (hour): %.2f" % (key.upper(), (total_dur_dict[key] / 60 / 60)))
