from config.global_conf import Global
from trader.market.market import Market
from config.shared_mongo_client import SharedMongoClient
from backtester.risk_free_arb_backtester import RfabBacktester
from trader.market_manager.virtual_market_manager import VirtualMarketManager


def main(target_currency: str, mm1_name: str, mm2_name: str, st_local: str, et_local: str):
    Global.configure_default_root_logging(should_log_to_file=False)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    start_time = Global.convert_local_datetime_to_epoch(st_local, timezone="kr")
    end_time = Global.convert_local_datetime_to_epoch(et_local, timezone="kr")

    mm1_taker_fee = Global.read_market_fee(mm1_name, True)
    mm1_maker_fee = Global.read_market_fee(mm1_name, False)
    mm2_taker_fee = Global.read_market_fee(mm2_name, True)
    mm2_maker_fee = Global.read_market_fee(mm2_name, False)

    mm1_market = getattr(Market, "VIRTUAL_%s" % mm1_name.upper())
    mm2_market = getattr(Market, "VIRTUAL_%s" % mm2_name.upper())

    bal_setting = {
        'mm1': {
            'krw_balance': 0,
            'coin_balance': 0.04475666666666667
        },
        'mm2': {
            'krw_balance': 333333.3333333333,
            'coin_balance': 0.0
        }
    }

    initial_setting_dict = {
        'max_trading_coin': 0.005,
        'min_trading_coin': 0,
        'new': {
            'threshold': 0,
            'factor': 1
        },
        'rev': {
            'threshold': 0,
            'factor': 1
        }
    }

    mm1 = VirtualMarketManager(mm1_market, mm1_taker_fee, mm1_maker_fee,
                               bal_setting["mm1"]["krw_balance"], bal_setting["mm1"]["coin_balance"],
                               target_currency, True)
    mm2 = VirtualMarketManager(mm2_market, mm2_taker_fee, mm2_maker_fee,
                               bal_setting["mm2"]["krw_balance"], bal_setting["mm2"]["coin_balance"],
                               target_currency, True)
    mm1_col = SharedMongoClient.get_target_col(mm1_market, target_currency)
    mm2_col = SharedMongoClient.get_target_col(mm2_market, target_currency)

    mm1_data_cursor, mm2_data_cursor = SharedMongoClient.get_data_from_db(mm1_col, mm2_col, start_time, end_time)
    RfabBacktester(mm1, mm2, target_currency).run(mm1_data_cursor, mm2_data_cursor, initial_setting_dict,
                                                  is_running_in_optimizer=False)


if __name__ == '__main__':
    st_local = '2018.08.18 20:42:10'
    et_local = '2018.08.18 21:16:01'
    main("btc", "gopax", "okcoin", st_local, et_local)
