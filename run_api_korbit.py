from api.korbit_api import KorbitApi
from api.currency import KorbitCurrency

korbit_api = KorbitApi.instance()
order_info = korbit_api.get_order_info(KorbitCurrency.ETH, "16507904")
print(order_info)
print(korbit_api.get_balance())
print(korbit_api.get_orderbook(KorbitCurrency.ETH))
print(korbit_api.order_limit_buy(KorbitCurrency.ETH, 430050, 0.01))
