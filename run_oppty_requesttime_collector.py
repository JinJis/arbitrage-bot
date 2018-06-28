from trader.market.market import Market
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from trader.risk_free_arb_bot import BaseArbBot
from collector.oppty_time_collector import OpptyRequestTimeCollector

Global.configure_default_root_logging(should_log_to_file=False)
SharedMongoClient.initialize(should_use_localhost_db=True)

start_time = Global.convert_local_datetime_to_epoch("2018.06.20 13:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.06.21 13:00:00", timezone="kr")

target_currency = "bch"
mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 5000000, 0.5, target_currency)
mm2 = VirtualMarketManager(Market.VIRTUAL_GP, 0.00075, 500000, 5, target_currency)
mm1_col = SharedMongoClient.get_target_col(Market.VIRTUAL_CO, target_currency)
mm2_col = SharedMongoClient.get_target_col(Market.VIRTUAL_GP, target_currency)
mm1_data_cursor, mm2_data_cursor = BaseArbBot.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

result_dict = OpptyRequestTimeCollector(mm1, mm2, target_currency).run(mm1_data_cursor, mm2_data_cursor,
                                                                       interval_depth=10)

print(result_dict)

total_duration = dict(new=0, rev=0)
for key in result_dict.keys():
    for time in result_dict[key]:
        diff = time[1] - time[0]
        total_duration[key] += diff
        print("[%s] duration (min): %.1f" % (key.upper(), (diff / 60)))
for key in total_duration.keys():
    print("Total [%s] duration (hour): %.2f" % (key.upper(), (total_duration[key] / 60 / 60)))
