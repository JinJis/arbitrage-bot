import time
from trader.market.order import Order, Market, OrderType
from api.currency import CoinoneCurrency
from config.shared_mongo_client import SharedMongoClient

SharedMongoClient.initialize(False)
test_order = Order(Market.VIRTUAL, CoinoneCurrency.ETH, OrderType.LIMIT_BUY, "co_buy_123", 100000, 1.1)
SharedMongoClient.async_order_insert(test_order.to_dict())
time.sleep(15)
test_order.fee = 1004
SharedMongoClient.async_order_update(test_order.to_dict())
