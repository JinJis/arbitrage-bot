from config.shared_mongo_client import SharedMongoClient

SharedMongoClient.initialize(should_use_localhost_db=False)
db_client = SharedMongoClient.instance()

s_iyo_col = db_client["trade"]["s_iyo"]
s_iyo_cur_list = s_iyo_col.find({"settings.end_time": {
    "$gte": 1535491781,
    "$lte":1535493052
}}).sort([("end_time", 1)])

result = []
for iyo in s_iyo_cur_list:
    result.append(iyo)

print(result)