import logging
from config.global_conf import Global
from pymongo import MongoClient

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
local_mongo = MongoClient(Global.read_mongodb_uri(True))
remote_mongo = MongoClient(Global.read_mongodb_uri(False))

for db_name in ["coinone", "gopax", "korbit", "bithumb", "okcoin", "coinnest"]:
    for col_name in ["bch_orderbook", "btc_orderbook", "eth_orderbook", "tron_orderbook", "xrp_orderbook",
                     "qtum_orderbook"]:

        try:
            local_target = local_mongo[db_name][col_name]
            remote_target = remote_mongo[db_name][col_name]
            from_time = local_target.find().sort([("requestTime", -1)]).limit(1)[0]["requestTime"]
            logging.info("Copying <%s.%s> from remote to local" % (db_name, col_name))
            logging.info("Local before: %d" % local_target.count())

            cursor = remote_target.find({
                "requestTime": {
                    "$gt": from_time
                }
            }).sort([("requestTime", 1)])

            for data in cursor:
                local_target.insert(data)

            logging.info("Remote added: %d" % cursor.count())
            logging.info("Local after: %d" % local_target.count())

        except IndexError:
            continue
