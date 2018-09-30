from config.global_conf import Global
import logging
from temp.trade_manager.trade_streamer_test.balance_updater import BalanceUpdater
from trader.market_manager.bithumb_market_manager import BithumbMarketManager
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager
from config.shared_mongo_client import SharedMongoClient

Global.configure_default_root_logging(log_level=logging.INFO, should_log_to_file=False)
SharedMongoClient.initialize(should_use_localhost_db=False)

# test Balance Updater

a = BalanceUpdater("chungjin93", "xrp", BithumbMarketManager(), OkcoinMarketManager())
#
a.update_balance_looper()


# test User

