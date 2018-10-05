import logging

from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.risk_free_arb_bot_v4 import RiskFreeArbBotV4


def main(target_currency: str, mm1_name: str, mm2_name: str):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=True)

    mm1 = Global.get_market_manager(mm1_name)
    mm2 = Global.get_market_manager(mm2_name)

    RiskFreeArbBotV4(target_currency, mm1, mm2, is_test=True).run()


if __name__ == '__main__':
    main("eos", "coinone", "gopax")
