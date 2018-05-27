import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.risk_free_arb_bot import RiskFreeArbBot2

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=False)
RiskFreeArbBot2(target_currency="bch", should_db_logging=True, is_backtesting=False).run()
