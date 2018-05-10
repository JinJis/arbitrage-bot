from api.gopax_api import GopaxAPI
from api.currency import GopaxCurrency
from config.global_conf import Global
from api.korbit_api import KorbitApi
from api.currency import KorbitCurrency

#
# test = GopaxAPI.instance(True)
# # test2 = KorbitApi.instance(True)
# print(test.get_orderbook(GopaxCurrency.ETH))
# # print(test2.get_orderbook(KorbitCurrency.ETH))

time = Global.iso8601_to_unix("2018-04-29T11:06:00.000Z")
print(time)



