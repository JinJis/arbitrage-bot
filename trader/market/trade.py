import time
from enum import Enum


class TradeTag(Enum):
    REV = "reverse"
    NEW = "new"


class Trade:
    def __init__(self, trade_tag: TradeTag):
        self.timestamp = int(time.time())
        self.trade_tag = trade_tag

    def set_timestamp(self, new_timestamp: int):
        self.timestamp = new_timestamp


class StatArbTradeMeta:
    def __init__(self, plain_spread, log_spread, log_mean, log_stdev, log_upper, log_lower):
        self._data = {
            "plain_spread": plain_spread,
            "log_spread": log_spread,
            "log_mean": log_mean,
            "log_stdev": log_stdev,
            "log_upper": log_upper,
            "log_lower": log_lower
        }

    def to_dict(self):
        return dict(self._data)


class ArbTrade(Trade):
    def __init__(self, trade_tag: TradeTag, orders: list, meta: StatArbTradeMeta):
        super().__init__(trade_tag)
        self.orders = orders
        self.meta = meta
