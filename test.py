from api.korbit_api import KorbitApi
from api.currency import KorbitCurrency, CoinoneCurrency
from api.coinone_api import CoinoneApi
import time
from bson import Decimal128

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

a = Decimal128("1000").to_decimal()
b = Decimal128("1200").to_decimal()
c = b - a
# - int(Decimal128(900))
# print(type(a))
print(c)
