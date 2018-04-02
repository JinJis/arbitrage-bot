from enum import Enum
from bson import Decimal128
from .market import Market
from api.currency import Currency
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


class OrderStatus(Enum):
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    UNFILLED = "unfilled"  # or "live" in coinone

    @classmethod
    def get(cls, order_status: str):
        _status = "unfilled" if order_status == "live" else order_status
        # noinspection PyTypeChecker
        return cls.__new__(cls, _status)


class Order:
    def __init__(self, market: Market, currency: Currency, order_type: OrderType,
                 order_id: str, price: int, amount: float):
        self.timestamp = int(time.time())
        self.status = OrderStatus.UNFILLED
        self.market = market
        self.currency = currency
        self.order_type = order_type
        self.order_id = order_id
        self.price = price
        self.amount = amount

    def __repr__(self):
        return "<Order %s>: %s in %s at %d (price %d, amount %f, status: %r)" % (
            self.order_id,
            self.order_type.value,
            self.market.value,
            self.timestamp,
            self.price,
            self.amount,
            self.status.value
        )

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "market": self.market.value,
            "order": self.order_type.value,
            "order_id": self.order_id,
            "price": Decimal128(str(self.price)),
            "amount": Decimal128(str(self.amount))
        }

    def is_sell_order(self):
        return self.order_type.is_sell_order()
