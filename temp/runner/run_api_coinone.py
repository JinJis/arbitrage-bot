from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency
from trader.market.order import Order, OrderType, Market

api = CoinoneApi.instance()
# order = Order(Market.COINONE, CoinoneCurrency.ETH, OrderType.LIMIT_SELL,
#               "14d2d523-03e0-437c-8f79-ba2e9c529ea4", 634000, 0.2007)
# print(api.cancel_order(CoinoneCurrency.ETH, order))
print(api.get_balance())
# print(api.order_limit_sell(CoinoneCurrency.ETH, 632000, 0.2007))
# print(api.order_limit_buy(CoinoneCurrency.ETH, 451500, 0.041))
# print(api.get_filled_orders(CoinoneCurrency.ETH))
# print(api.get_past_trades(CoinoneCurrency.ETH))
# print(api.get_open_orders(CoinoneCurrency.ETH))
# print(api.get_order_info(CoinoneCurrency.ETH, "2fc7576e-45ec-4a31-b34b-1e18632bbb85"))
