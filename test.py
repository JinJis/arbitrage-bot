import pymongo
from pymongo.collection import Collection
from config.shared_mongo_client import SharedMongoClient

SharedMongoClient.initialize(should_use_localhost_db=False)
db_clinet = SharedMongoClient.instance()


fti_settings_col: Collection = db_clinet["trade"]["fti_setting"]


ini_set = fti_settings_col.find_one(
    sort=[('_id', pymongo.DESCENDING)]
)["fti_iyo_list"]

print(ini_set[0]["initial_setting"])
