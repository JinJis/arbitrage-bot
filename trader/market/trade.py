import time
from enum import Enum


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
    def __init__(self, trade_tag: TradeTag, orders: list, trade_meta: TradeMeta):
        self.timestamp = int(time.time())
        self.trade_tag = trade_tag
        self.orders = orders
        self.trade_meta = trade_meta

    def set_timestamp(self, new_timestamp: int):
        self.timestamp = new_timestamp

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "tag": self.trade_tag.value,
            "orders": [order.order_id for order in self.orders],
            "meta": self.trade_meta.to_dict()
        }
