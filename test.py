from config.shared_mongo_client import SharedMongoClient

trade = {"hello": 123, "my": 151}
order = {"order": 32}

SharedMongoClient.initialize(should_use_localhost_db=False)
SharedMongoClient.async_trade_insert(trade)
SharedMongoClient.async_order_insert(order)
