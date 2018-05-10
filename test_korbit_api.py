from api.korbit_api import KorbitApi
from api.currency import KorbitCurrency
from trader.market.order import Order, OrderType, Market
from api.korbit_error import KorbitError

api = KorbitApi.instance()
# print(api.get_balance())
# print(api.order_limit_buy(KorbitCurrency.ETH, 820000, 0.01))
print(api.get_order_info(KorbitCurrency.ETH, "18608098"))
# print(api.get_past_trades(KorbitCurrency.ETH))
# print(api.get_open_orders(KorbitCurrency.ETH))
# print(api.cancel_order(KorbitCurrency.ETH,
#                        Order(Market.KORBIT, KorbitCurrency.ETH, OrderType.LIMIT_BUY, "18608098", 820000, 0.01)))
