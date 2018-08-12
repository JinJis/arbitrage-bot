import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from optimizer.arbitrage_combination_optimizer.integrated_yield_optimizer import IYOStatAppender

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=True)

start_time = Global.convert_local_datetime_to_epoch("2018.07.24 11:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.07.24 12:00:00", timezone="kr")

db_client = SharedMongoClient.instance()
iyo_col = db_client["statistics"]["iyo"]
iyo_cur = iyo_col.find({
    "settings.start_time": {
        "$gte": start_time,
        "$lte": end_time}}).sort([("start_time", 1)])

for iyo_data in iyo_cur:
    logging.critical("Now starting: %s" % Global.convert_epoch_to_local_datetime(iyo_data["settings"]["start_time"]))
    stat_result = IYOStatAppender.run(iyo_data=iyo_data)

    # append this stat dict to the current IYO_data
    db_client["statistics"]["iyo"].update(
        {'_id': iyo_data['_id']}, {
            '$set': {
                'stat': stat_result
            }}, upsert=False, multi=False)

    logging.critical("Appended Stat result to target IYO_data at MongoDB")
