import logging
from config.global_conf import Global
from pymongo import MongoClient

local_mongo = MongoClient(Global.read_mongodb_uri(True))
remote_mongo = MongoClient(Global.read_mongodb_uri(False))

for db_name in ["coinone", "gopax", "korbit"]:
    for col_name in ["bch_orderbook", "btc_orderbook", "eth_orderbook"]:

        logging.info("Copying <%s.%s> from remote to local" % (db_name, col_name))
        local_target = local_mongo[db_name][col_name]
        remote_target = remote_mongo[db_name][col_name]
        from_time = local_target.find().sort([("requestTime", -1)]).limit(1)[0]["requestTime"]

        print("Local before: %d" % local_target.count())

        cursor = remote_target.find({
            "requestTime": {
                "$gt": from_time
            }
        }).sort([("requestTime", 1)])

        for data in cursor:
            local_target.insert(data)

        print("Remote added: %d" % cursor.count())
        print("Local after: %d" % local_target.count())
