from config.shared_mongo_client import SharedMongoClient

SharedMongoClient.initialize(should_use_localhost_db=False)
test_db = SharedMongoClient.get_test_streamer_db()["balance_commander"]

test_db.insert_one(dict(is_bal_update=True))
