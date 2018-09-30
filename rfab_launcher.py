import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from config.config_market_manager import ConfigMarketManager
from temp.trade_manager.user_manager import UserManager

Global.configure_default_root_logging(log_level=logging.INFO, should_log_to_file=False)
SharedMongoClient.initialize(should_use_localhost_db=False)

# settings
user_id = "chungjin93"
target_currency = "xrp"
mm1_name = "bithumb"
mm2_name = "okcoin"

mm1 = getattr(ConfigMarketManager, mm1_name.upper())
mm2 = getattr(ConfigMarketManager, mm2_name.upper())

# validate by Usermanager before RFAB
UserManager().validation_before_rfab(user_id, target_currency, mm1_name, mm2_name)


# Multiprocessing
