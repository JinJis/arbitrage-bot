from enum import Enum
from bson import Decimal128
from .market import Market
import time


class OrderType(Enum):
    LIMIT_BUY = "limit_buy"
    LIMIT_SELL = "limit_sell"
    MARKET_BUY = "market_buy"
    MARKET_SELL = "market_sell"


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
