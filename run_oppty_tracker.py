import logging
import time
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.trade_manager.trade_handler import TradeHandler
from trader.market_manager.bithumb_market_manager import BithumbMarketManager
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager

target_currency = "btc"
mm1 = BithumbMarketManager()
mm2 = OkcoinMarketManager()

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
SharedMongoClient.initialize(should_use_localhost_db=False)

while True:
    TradeHandler(target_currency, mm1, mm2, False, False).launch_inner_outer_ocat()
    time.sleep(10 * 60)
