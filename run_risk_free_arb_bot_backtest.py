from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.market.order import Market
from backtester.risk_free_arb_backtest import RfabBacktester

Global.configure_default_root_logging(should_log_to_file=True)
SharedMongoClient.initialize(should_use_localhost_db=False)

start_time = Global.convert_local_datetime_to_epoch("2018.06.24 09:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.06.24 16:45:00", timezone="kr")

target_currency = "bch"

mm1_balance_dict = {
    "mkt_tag": Market.VIRTUAL_CO,
    "market_fee": 0.001,
    "krw_balance": 5000000,
    "coin_balance": 0.5
}

mm2_balance_dict = {
    "mkt_tag": Market.VIRTUAL_GP,
    "market_fee": 0.00075,
    "krw_balance": 500000,
    "coin_balance": 5
}

initial_setting_dict = {
    "max_trading_coin": 0.01,
    "min_trading_coin": 0,
    "new": {
        "threshold": 50,
        "factor": 1
    },
    "rev": {
        "threshold": 50,
        "factor": 1
    }
}

RfabBacktester(mm1_balance_dict, mm2_balance_dict, initial_setting_dict, start_time, end_time,
               target_currency=target_currency, is_init_setting_opt=False).run()
