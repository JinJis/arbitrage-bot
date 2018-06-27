from trader.market.market import Market
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.base_arb_bot import BaseArbBot
from backtester.risk_free_arb_backtester import RfabBacktester
from optimizer.initial_setting_optimizer import InitialSettingOptimizer
from trader.market_manager.virtual_market_manager import VirtualMarketManager


def get_target_col(market_tag: Market, target_currency: str):
    method_name = {
        Market.VIRTUAL_CO: "get_coinone_db",
        Market.VIRTUAL_KB: "get_korbit_db",
        Market.VIRTUAL_GP: "get_gopax_db"
    }[market_tag]
    return getattr(SharedMongoClient, method_name)()[target_currency + "_orderbook"]


def create_trading_bot(init_setting_dict: dict):
    Global.configure_default_root_logging(should_log_to_file=False)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    start_time = Global.convert_local_datetime_to_epoch("2018.06.24 16:45:00", timezone="kr")
    end_time = Global.convert_local_datetime_to_epoch("2018.06.25 09:45:00", timezone="kr")

    target_currency = "bch"
    mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 5000000, 0.5, target_currency)
    mm2 = VirtualMarketManager(Market.VIRTUAL_GP, 0.00075, 500000, 5, target_currency)
    mm1_col = get_target_col(Market.VIRTUAL_CO, target_currency)
    mm2_col = get_target_col(Market.VIRTUAL_GP, target_currency)

    mm1_data_cursor, mm2_data_cursor = BaseArbBot.get_data_from_db(mm1_col, mm2_col, start_time, end_time)
    RfabBacktester(mm1, mm2, target_currency, init_setting_dict, False).run(mm1_data_cursor, mm2_data_cursor)


setting_factor_dict = {
    "max_trading_coin": {
        "start": 0,
        "end": 0.1,
        "step_limit": 0.0001
    },
    "min_trading_coin": {
        "start": 0,
        "end": 0,
        "step_limit": 0.0001
    },
    "new": {
        "threshold": {
            "start": 0,
            "end": 1000,
            "step_limit": 1

        },
        "factor": {
            "start": 1,
            "end": 3,
            "step_limit": 0.01
        }
    },
    "rev": {
        "threshold": {
            "start": 0,
            "end": 1000,
            "step_limit": 1
        },
        "factor": {
            "start": 1,
            "end": 3,
            "step_limit": 0.01
        }
    }
}

trading_bot = create_trading_bot(initial_setting_dict)
InitialSettingOptimizer(trading_bot, initial_setting_dict, division=4, depth=10).run()
