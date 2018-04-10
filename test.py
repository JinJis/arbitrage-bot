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
# print(korbit_api.get_balance())
# print(korbit_api.get_orderbook(KorbitCurrency.ETH))
# print(korbit_api.order_limit_buy(KorbitCurrency.ETH, 430050, 0.01))

# from api.coinone_api import CoinoneApi
# from api.currency import CoinoneCurrency
# from trader.market.order import Order, OrderType, Market
#
# api = CoinoneApi.instance()
# order = Order(Market.COINONE, CoinoneCurrency.ETH, OrderType.LIMIT_BUY,
# "9feba50b-28d8-4b19-8f1b-d154abd6fa09", 425100, 0.01)
# print(api.cancel_order(CoinoneCurrency.ETH, order))
# balance = api.get_balance()
# print(balance)
# print(api.order_limit_buy(CoinoneCurrency.ETH, 425100, 0.01))
# print(api.get_filled_orders(CoinoneCurrency.ETH))
# print(api.get_past_trades(CoinoneCurrency.ETH))
# print(api.get_open_orders(CoinoneCurrency.ETH))

from collector.scheduler.filled_order_scheduler import FilledOrderScheduler

FilledOrderScheduler("eth", False).run()

# from collector.filled_order_collector import FilledOrderCollector
#
# collector = FilledOrderCollector(Global.read_mongodb_uri(False), "eth")
# collector.collect_kb_filled_orders()
# time.sleep(5)
# collector.collect_kb_filled_orders()
