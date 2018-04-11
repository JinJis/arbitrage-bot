from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.stat_arb_bot import StatArbBot

Global.configure_default_root_logging(should_log_to_file=False)
SharedMongoClient.initialize(should_use_localhost_db=False)
StatArbBot(is_backtesting=False).run()
