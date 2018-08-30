import logging
from config.global_conf import Global
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.bithumb_market_manager import BithumbMarketManager
from trader.market_manager.gopax_market_manager import GopaxMarketManager
from config.shared_mongo_client import SharedMongoClient
from trader.risk_free_arb_bot_v3 import RiskFreeArbBotV3

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=False)
streamer_db = SharedMongoClient.get_streamer_db()

RiskFreeArbBotV3(
    target_currency="xrp",
    mm1=CoinoneMarketManager(),
    mm2=OkcoinMarketManager(),
    fti_settings_col=streamer_db["fti_setting"]
).run()
