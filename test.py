from trader.market.market import Market
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from trader.risk_free_arb_bot import BaseArbBot
from collector.oppty_time_collector import OpptyRequestTimeCollector


def get_target_col(market_tag: Market, target_coin: str):
    method_name = {
        Market.VIRTUAL_CO: "get_coinone_db",
        Market.VIRTUAL_KB: "get_korbit_db",
        Market.VIRTUAL_GP: "get_gopax_db"
    }[market_tag]
    return getattr(SharedMongoClient, method_name)()[target_coin + "_orderbook"]


Global.configure_default_root_logging(should_log_to_file=False)
SharedMongoClient.initialize(should_use_localhost_db=False)

start_time = Global.convert_local_datetime_to_epoch("2018.06.26 12:30:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.06.27 12:50:00", timezone="kr")

target_currency = "bch"
mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 5000000, 0.5, target_currency)
mm2 = VirtualMarketManager(Market.VIRTUAL_GP, 0.00075, 500000, 5, target_currency)
mm1_col = get_target_col(Market.VIRTUAL_CO, target_currency)
mm2_col = get_target_col(Market.VIRTUAL_GP, target_currency)
mm1_data_cursor, mm2_data_cursor = BaseArbBot.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

OpptyRequestTimeCollector(mm1, mm2, target_currency).run(mm1_data_cursor, mm2_data_cursor)
