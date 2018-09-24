import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.market_manager import MarketManager
from trader.trade_streamer.tester import TestTradeStreamer
from trader.market_manager.bithumb_market_manager import BithumbMarketManager
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager


def main(target_currency: str, mm1: MarketManager, mm2: MarketManager, mm1_name: str, mm2_name: str,
         mm1_krw_bal: float, mm1_coin_bal: float, mm2_krw_bal: float, mm2_coin_bal: float):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    trade_streamer = TestTradeStreamer(target_currency, mm1, mm2, mm1_name, mm2_name,
                                       mm1_krw_bal, mm1_coin_bal, mm2_krw_bal, mm2_coin_bal)

    trade_streamer.real_time_streamer()


if __name__ == '__main__':
    main("eth", BithumbMarketManager(), OkcoinMarketManager(), "bithumb", "okcoin",
         mm1_krw_bal=1000000, mm1_coin_bal=0, mm2_krw_bal=0, mm2_coin_bal=3.3)
