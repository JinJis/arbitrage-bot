import logging
from config.global_conf import Global
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager
from trader.market_manager.bithumb_market_manager import BithumbMarketManager
from config.shared_mongo_client import SharedMongoClient
from temp.arbbot_ideas.risk_free_arb_bot_v3 import RiskFreeArbBotV3

Global.configure_default_root_logging(should_log_to_file=True, log_level=logging.WARNING)
SharedMongoClient.initialize(should_use_localhost_db=True)

RiskFreeArbBotV3(
    target_currency="xrp",
    mm1=BithumbMarketManager(),
    mm2=OkcoinMarketManager(),
    streamer_db=SharedMongoClient.get_streamer_db()
).run()
