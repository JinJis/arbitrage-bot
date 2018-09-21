import logging
from config.global_conf import Global
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager
from trader.market_manager.bithumb_market_manager import BithumbMarketManager
from config.shared_mongo_client import SharedMongoClient
from trader.risk_free_arb_bot_v4 import RiskFreeArbBotV4

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
SharedMongoClient.initialize(should_use_localhost_db=False)

RiskFreeArbBotV4(
    target_currency="xrp",
    mm1=BithumbMarketManager(),
    mm2=OkcoinMarketManager(),
    is_test=True).run()
