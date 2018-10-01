import sys
import logging

from config.config_market_manager import ConfigMarketManager
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.trade_streamer.trade_streamer_v2 import TradeStreamerV2


def main(target_currency: str, mm1_name: str, mm2_name: str):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    mm1 = getattr(ConfigMarketManager, mm1_name.upper()).value
    mm2 = getattr(ConfigMarketManager, mm2_name.upper()).value

    # run TradeStreamer
    TradeStreamerV2(mm1=mm1, mm2=mm2, target_currency=target_currency, is_test=True).run()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
