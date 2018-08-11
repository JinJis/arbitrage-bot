import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from analyzer.iyo_analyzer import IYOMongoDBAnalyzer

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=False)

start_time = Global.convert_local_datetime_to_epoch("2018.07.24 09:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.07.24 12:00:00", timezone="kr")

iyo_client = SharedMongoClient.instance()
iyo_col = iyo_client["statistics"]["iyo"]
iyo_cur = iyo_col.find({
    "settings.start_time": {
        "$gte": start_time,
        "$lte": end_time}}).sort([("start_time", 1)])

for iyo_data in iyo_cur:
    logging.critical("Now starting: %d" % iyo_data["settings"]["start_time"])
    stat_result = IYOMongoDBAnalyzer.run(iyo_data=iyo_data)
    logging.critical("IYO stat result: \n%s" % stat_result)
