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
        self.updated_at = self.timestamp
        self.status = OrderStatus.UNFILLED
        self.market = market
        self.currency = currency
        self.order_type = order_type
        self.order_id = order_id
        self.price = price
        self.order_amount = amount
        self.filled_amount = 0
        self.remain_amount = amount
        self.avg_filled_price = 0
        self.fee = 0
        self.fee_rate = 0

    def __repr__(self):
        return "<Order %s>(%s in %s) - status %s, price %d, ordered %f, filled %f, remain %f" % (
            self.order_id,
            self.order_type.value,
            self.market.value,
            self.status.value,
            self.price,
            self.order_amount,
            self.filled_amount,
            self.remain_amount
        )

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "updated_at": self.updated_at,
            "order_id": self.order_id,
            "market": self.market.value,
            "currency": self.currency.name,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "price": Decimal128(str(self.price)),
            "order_amount": Decimal128(str(self.order_amount)),
            "filled_amount": Decimal128(str(self.filled_amount)),
            "remain_amount": Decimal128(str(self.remain_amount)),
            "avg_filled_price": Decimal128(str(self.avg_filled_price)),
            "fee": Decimal128(str(self.fee)),
            "fee_rate": Decimal128(str(self.fee_rate))
        }

    def is_sell_order(self):
        return self.order_type.is_sell_order()

    def update_from_api(self, res_json: dict):
        """ res_json
        {
            "status": OrderStatus,
            "avg_filled_price": int,
            "order_amount": float,
            "filled_amount": float,
            "remain_amount": float,
            "fee": float
        }
        """
        self.updated_at = int(time.time())
        self.status = res_json["status"]
        self.order_amount = res_json["order_amount"]
        self.avg_filled_price = res_json["avg_filled_price"]
        self.filled_amount = res_json["filled_amount"]
        self.remain_amount = res_json["remain_amount"]
        self.fee = res_json["fee"]

        if self.status is OrderStatus.FILLED:
            # krw is charged as fee if it's a sell order
            if self.is_sell_order():
                self.fee_rate = round(self.fee / self.price, 4)
            # coin is charged as fee if it's a buy order
            else:
                self.fee_rate = round(self.fee / self.order_amount, 4)

    def get_filled_status(self):
        return "<Order %s>(%s in %s) is now filled - avg_filled_price %s, filled_amount %f, fee %f, fee_rate %f" % (
            self.order_id,
            self.order_type.value,
            self.market.value,
            self.avg_filled_price,
            self.filled_amount,
            self.fee,
            self.fee_rate
        )
