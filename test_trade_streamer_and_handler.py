import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.trade_manager.tester.test_trade_streamer import TestTradeStreamer


def main(target_currency: str, mm1_name: str, mm2_name: str,
         mm1_krw_bal: float, mm1_coin_bal: float, mm2_krw_bal: float, mm2_coin_bal: float):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    db_clinet = SharedMongoClient.instance()
    trade_streamer = TestTradeStreamer(target_currency, mm1_name, mm2_name,
                                       mm1_krw_bal, mm1_coin_bal, mm2_krw_bal, mm2_coin_bal, db_clinet)

    trade_streamer.real_time_streamer()


if __name__ == '__main__':
    main("tron", "bithumb", "okcoin",
         mm1_krw_bal=1000000, mm1_coin_bal=0, mm2_krw_bal=0, mm2_coin_bal=3.3)
