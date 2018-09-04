import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.trade_manager.trade_streamer import TradeStreamer
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager
from trader.market_manager.bithumb_market_manager import BithumbMarketManager


def main():

    mm1 = BithumbMarketManager()
    mm2 = OkcoinMarketManager()
    target_currency = "xrp"

    Global.configure_default_root_logging(should_log_to_file=True, log_level=logging.WARNING)
    SharedMongoClient.initialize(should_use_localhost_db=True)
    # run TradeStreamer
    TradeStreamer(mm1=mm1, mm2=mm2, target_currency=target_currency).run()


if __name__ == '__main__':
    main()
