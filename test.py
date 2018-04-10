from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.stat_arb_bot import StatArbBot
import time

# Global.configure_default_root_logging(should_log_to_file=True)
# SharedMongoClient.COINONE_DB_NAME = "coinone_180402"
# SharedMongoClient.KORBIT_DB_NAME = "korbit_180402"
# # use remote address for db
# SharedMongoClient.initialize(should_use_localhost_db=False)
# start_time = Global.convert_local_datetime_to_epoch("2018.03.25 00:00:00", timezone="kr")
# end_time = Global.convert_local_datetime_to_epoch("2018.03.30 00:00:00", timezone="kr")
# # StatArbBot(is_backtesting=False).run()
# start = time.time()
# StatArbBot(should_db_logging=False, is_backtesting=True, start_time=start_time, end_time=end_time).run()
# print(int(time.time() - start))

# from api.korbit_api import KorbitApi
# from api.currency import KorbitCurrency
#
# korbit_api = KorbitApi.instance()
# order_info = korbit_api.get_order_info(KorbitCurrency.ETH, "16507904")
# print(order_info)


from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency

api = CoinoneApi.instance()
balance = api.get_balance()
print(balance)
