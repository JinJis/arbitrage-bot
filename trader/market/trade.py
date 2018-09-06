import time
from enum import Enum
from threading import Lock
from bson import Decimal128


class TradeTag(Enum):
    REV = "reverse"
    NEW = "new"


class TradeMeta:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return dict(self._data)


class StatArbTradeMeta(TradeMeta):
    def __init__(self, plain_spread, log_spread, log_mean, log_stdev, log_upper, log_lower):
        super().__init__({
            "plain_spread": plain_spread,
            "log_spread": log_spread,
            "log_mean": log_mean,
            "log_stdev": log_stdev,
            "log_upper": log_upper,
            "log_lower": log_lower
        })


class Trade:
    increment_lock = Lock()
    trade_id_count = 0

    def __init__(self, trade_tag: TradeTag, orders: list, trade_meta: TradeMeta):
        self.trade_id = Trade.generate_trade_id()
        self.timestamp = int(time.time())
        self.trade_tag = trade_tag
        self.orders = orders
        self.trade_meta = trade_meta

    def __repr__(self):
        return "<Trade %s> - tag %s, orders %s" % (
            self.trade_id,
            self.trade_tag.value,
            [order.order_id for order in self.orders]
        )

    def set_timestamp(self, new_timestamp: int):
        self.timestamp = new_timestamp

    def to_dict(self):
        return {
            "type": "trade",
            "trade_id": self.trade_id,
            "timestamp": self.timestamp,
            "tag": self.trade_tag.value,
            "orders": [{
                "timestamp": order.timestamp,
                "order_id": order.order_id,
                "market": order.market.value,
                "currency": order.currency.name,
                "order_type": order.order_type.value,
                "status": order.status.value,
                "price": Decimal128(str(order.price)),
                "order_amount": Decimal128(str(order.order_amount)),
                "filled_amount": Decimal128(str(order.filled_amount)),
                "remain_amount": Decimal128(str(order.remain_amount)),
                "avg_filled_price": Decimal128(str(order.avg_filled_price)),
                "fee": Decimal128(str(order.fee)),
                "fee_rate": Decimal128(str(order.fee_rate))
            } for order in self.orders],
            "meta": self.trade_meta.to_dict()
        }

    @classmethod
    def generate_trade_id(cls):
        with cls.increment_lock:
            cls.trade_id_count += 1
            return str(cls.trade_id_count)
