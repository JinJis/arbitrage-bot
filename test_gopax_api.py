from api.gopax_api import GopaxAPI
from api.currency import GopaxCurrency
from trader.market.order import Order, Market, OrderType
from config.global_conf import Global
import logging

# Global.configure_default_root_logging(logging.DEBUG)
gopax_api = GopaxAPI.instance()
# print(gopax_api.get_balance())
# print(gopax_api.get_past_trades(GopaxCurrency.BCH))
# print(gopax_api.get_open_orders(GopaxCurrency.BCH))
# print(gopax_api.order_limit_buy(GopaxCurrency.BCH, 100, 0.1))
print(gopax_api.get_order_info(GopaxCurrency.BCH, "77028931"))
# print(gopax_api.cancel_order(GopaxCurrency.BCH, Order(Market.GOPAX, GopaxCurrency.BCH,
#                                                       OrderType.LIMIT_SELL, "77033266", 1870000, 0.005)))
# print(gopax_api.order_limit_sell(GopaxCurrency.BCH, 1870000, 0.005))
