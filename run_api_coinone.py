from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency
from trader.market.order import Order, OrderType, Market

api = CoinoneApi.instance()
order = Order(Market.COINONE, CoinoneCurrency.ETH, OrderType.LIMIT_BUY,
              "9feba50b-28d8-4b19-8f1b-d154abd6fa09", 425100, 0.01)
print(api.cancel_order(CoinoneCurrency.ETH, order))
print(api.get_balance())
print(api.order_limit_buy(CoinoneCurrency.ETH, 425100, 0.01))
print(api.get_filled_orders(CoinoneCurrency.ETH))
print(api.get_past_trades(CoinoneCurrency.ETH))
print(api.get_open_orders(CoinoneCurrency.ETH))
