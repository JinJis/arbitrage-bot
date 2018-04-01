from api.korbit_api import KorbitApi
from api.currency import KorbitCurrency, CoinoneCurrency, Currency
from api.coinone_api import CoinoneApi
import time
from datetime import datetime
from bson import Decimal128
from decimal import Decimal
# from trader.market_manager.virtual_market_manager import VirtualMarketManager
from collector.db_to_csv import DbToCsv

# korbit_api = KorbitApi()
# print(korbit_api.get_balance())
# print(korbit_api.get_open_orders(KorbitCurrency.ETH))
# print(korbit_api.get_past_trades(KorbitCurrency.ETH))
#
# coinone_api = CoinoneApi()
# print(coinone_api.get_balance())
# print(coinone_api.get_open_orders(CoinoneCurrency.ETH))
# print(coinone_api.get_past_trades(CoinoneCurrency.ETH))

# korbit_api = KorbitApi(is_public_access_only=True)


# print())
# print(korbit_api.)
#
# class FilledOrderAnalyzer:
#     @staticmethod
#     def get_filled_orders_within(prev_filled_orders, curr_filled_orders):
#         lala = curr_filled_orders.index(prev_filled_orders[0])
#         return curr_filled_orders[:(lala+1)]
#
#
# list1 = korbit_api.get_filled_orders(KorbitCurrency.ETH)
# print(list1[0])
# # time.sleep(30)
# list2 = korbit_api.get_filled_orders(KorbitCurrency.ETH)
# print(list2[0])
# start = time.time()
# list3 = FilledOrderAnalyzer.get_filled_orders_within(list1, list2)
# end = time.time()
# print(list3)
# print(end-start)

# a = Decimal128("1000").to_decimal()
# b = Decimal128("1200").to_decimal()
# c = abs(a - b)
# - int(Decimal128(900))
# print(type(a))
# print(c)

# d = Decimal("123123")
# f = Decimal128("123123")
# if isinstance(f, Decimal):
#     print("yeye")

# Global.configure_default_root_logging()
# logging.info(Balance(Market.KORBIT, {
#     "krw": {
#         "available": Decimal(128),
#         "trade_in_use": Decimal(300),
#         "balance": Decimal(2.8898745)
#     },
#     "eth": {
#         "available": Decimal(128),
#         "trade_in_use": Decimal(300),
#         "balance": Decimal(2.889874)
#     }
# }))

# a = VirtualMarketManager("a", 0.03)
# print(a.market_fee)
# b = VirtualMarketManager("b", 0.08)
# print(b.market_fee)
# print(CoinoneCurrency.ETH.value)

from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
import logging
from config.global_conf import Global

# def get_price_of_minask_maxbid(orderbook: dict):
#     return orderbook["asks"][0]["price"].to_decimal(), orderbook["bids"][0]["price"].to_decimal()
#
#


# logging.info(korbit_api.get_order_info(KorbitCurrency.ETH, "15739205"))


# korbit_mm = KorbitMarketManager()
# korbit_orderbook = korbit_mm.get_orderbook(KorbitCurrency.ETH)
# korbit_minask, korbit_maxbid = get_price_of_minask_maxbid(korbit_orderbook)
# logging.info("korbit minask: %s, maxbid: %s" % (korbit_minask, korbit_maxbid))
#
# korbit_avg = (korbit_maxbid + korbit_minask) / 2
# korbit_mm.order_sell(KorbitCurrency.ETH, int(korbit_avg // 100 * 100), 0.01)
#
# coinone_mm = CoinoneMarketManager()
# coinone_orderbook = coinone_mm.get_orderbook(CoinoneCurrency.ETH)
# coinone_minask, coinone_maxbid = get_price_of_minask_maxbid(coinone_orderbook)
# logging.info("coinone minask: %s, maxbid: %s" % (coinone_minask, coinone_maxbid))
#
# coinone_avg = (coinone_maxbid + coinone_minask) / 2
# coinone_mm.order_sell(CoinoneCurrency.ETH, int(coinone_avg // 100 * 100), 0.01)

# Global.configure_default_root_logging()
# korbit_api = KorbitApi()
# coinone_api = CoinoneApi()

# logging.info(korbit_api.cancel_order(KorbitCurrency.ETH, "15742897"))
# logging.info(
#     coinone_api.cancel_order(CoinoneCurrency.ETH, 583700, 0.020000, "c01a9891-84ca-4e61-bb61-cfe3b7adb288", False))

# while True:
# logging.info(korbit_api.get_past_trades(KorbitCurrency.ETH))
# logging.info(coinone_api.get_past_trades(CoinoneCurrency.ETH))
# logging.info(korbit_mm.get_balance())
# logging.info(coinone_mm.get_balance())
# time.sleep(1)

# from trader.arbitrage_bot import ArbitrageBot
#
# ab = ArbitrageBot()
# ab.run()

# fetcher = DbFetcher()
# cursor = fetcher.test()
# for item in cursor:
#     print(item["last"])

# start_time = Global.convert_local_datetime_to_epoch("2018.03.26 09:00:00")
# end_time = Global.convert_local_datetime_to_epoch("2018.03.26 21:00:00")
# db_to_csv = DbToCsv()
# db_to_csv.save_ticker_as_csv("korbit", "eth", start_time, end_time)
# db_to_csv.save_ticker_as_csv("coinone", "eth", start_time, end_time)

# print(Global.get_z_score_for_probability(0.954499736104))


from trader.stat_arb_bot import StatArbBot

# Global.configure_default_root_logging(should_log_to_file=True)
# # Global.configure_default_root_logging()
# start_time = Global.convert_local_datetime_to_epoch("2018.03.25 00:00:00", timezone="kr")
# end_time = Global.convert_local_datetime_to_epoch("2018.03.30 00:00:00", timezone="kr")
# StatArbBot(is_from_local=True, is_backtesting=True, start_time=start_time, end_time=end_time).run()

from api.coinone_error import CoinoneErrorCode, CoinoneError

from trader.market.order import OrderType

print(OrderType.LIMIT_BUY)
