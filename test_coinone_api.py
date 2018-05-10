from api.coinone_api import CoinoneApi, CoinoneCurrency
from trader.market.order import Order, Market, OrderType
from api.coinone_error import CoinoneError

api = CoinoneApi.instance()
# print(api.get_balance())
# print(api.order_limit_buy(CoinoneCurrency.ETH, 800000, 0.01))
print(api.get_order_info(CoinoneCurrency.ETH, "436723d9-1f8b-48a5-9370-881db629e4a6"))
# print(api.get_past_trades(KorbitCurrency.ETH))
# print(api.get_open_orders(KorbitCurrency.ETH))
# print(api.cancel_order(CoinoneCurrency.ETH,
#                        Order(Market.KORBIT, CoinoneCurrency.ETH, OrderType.LIMIT_BUY,
#                              "436723d9-1f8b-48a5-9370-881db629e4a6", 800000, 0.01)))
