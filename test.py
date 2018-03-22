from api.korbit_api import KorbitApi
from api.currency import KorbitCurrency, CoinoneCurrency, Currency
from api.coinone_api import CoinoneApi
import time
from bson import Decimal128
from decimal import Decimal
from trader.market_manager.virtual_market_manager import VirtualMarketManager


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

def yoyo(currency: Currency):
    print(currency["ETH"])


test = CoinoneCurrency()
yoyo(test)
