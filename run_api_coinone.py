from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency
from trader.market.order import Order, OrderType, Market

api = CoinoneApi.instance()
order = Order(Market.COINONE, CoinoneCurrency.ETH, OrderType.LIMIT_BUY,
              "258262bd-a19f-437c-89c7-f3bbf235f289", 425000, 0.0410)
print(api.cancel_order(CoinoneCurrency.ETH, order))
print(api.get_balance())
print(api.order_limit_buy(CoinoneCurrency.ETH, 451500, 0.041))
print(api.get_filled_orders(CoinoneCurrency.ETH))
print(api.get_past_trades(CoinoneCurrency.ETH))
print(api.get_open_orders(CoinoneCurrency.ETH))
print(api.get_order_info(CoinoneCurrency.ETH, "2fc7576e-45ec-4a31-b34b-1e18632bbb85"))
