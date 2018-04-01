from enum import Enum
from bson import Decimal128
from .market import Market
import time


class OrderType(Enum):
    LIMIT_BUY = ("limit", "buy")
    LIMIT_SELL = ("limit", "sell")
    MARKET_BUY = ("market", "buy")
    MARKET_SELL = ("market", "sell")

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = "%s_%s" % args
        obj._strategy = args[0]
        obj._action = args[1]
        return obj

    def is_sell_order(self) -> bool:
        return self._action == "sell"


class Order:
    def __init__(self, market: Market, order_type: OrderType, order_id: str, price: int, amount: float):
        self.timestamp = int(time.time())
        self.market = market
        self.order_type = order_type
        self.order_id = order_id
        self.price = price
        self.amount = amount

        # TODO: request for filled orders until the order is completely filled
        self.is_filled = False
        self.filled_orders = list()

    def __repr__(self):
        return "<Order %s>: %s in %s at %d (price %d, amount %f, is_filled: %r)" % (
            self.order_id,
            self.order_type.value,
            self.market.value,
            self.timestamp,
            self.price,
            self.amount,
            self.is_filled
        )

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "market": self.market.value,
            "order": self.order_type.value,
            "order_id": self.order_id,
            "price": Decimal128(str(self.price)),
            "amount": Decimal128(str(self.amount)),
            "is_filled": self.is_filled
        }

    def is_sell_order(self):
        return self.order_type.is_sell_order()
