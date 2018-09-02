import numpy
import logging
from trader.market.trade import Trade, TradeTag
from trader.market.switch_over import SwitchOver
from trader.market.order import Order
from collections import deque
from config.shared_mongo_client import SharedMongoClient
from .order_watcher import OrderWatcher


class TradeManager:
    # remember only last <*_LIMIT> number of trade / switch_over if it's not in a backtesting mode
    TRADE_INSTANCE_LIMIT = 50
    SWITCH_OVER_INSTANCE_LIMIT = 100

    def __init__(self, should_db_logging: bool, is_backtesting: bool):
        self.should_db_logging = should_db_logging
        self.is_backtesting = is_backtesting

        # use double-ended queue for performance
        # note that pop(0) in list is O(n) while pop() is O(1)
        # deque has its own `pop_left()` for this functionality
        self._trade_list = deque()
        self._switch_over_list = deque()

    def add_trade(self, cur_trade: Trade):
        # see if this is not the first trade, and the trade tag has changed from the tag of last trade
        last_trade = self.get_last_trade()
        if last_trade is not None and cur_trade.trade_tag is not last_trade.trade_tag:
            switch_over = SwitchOver(last_trade.trade_tag.name, cur_trade.trade_tag.name,
                                     last_trade.timestamp, cur_trade.timestamp)
            self.add_switch_over(switch_over)

        # limit number of trade instance
        if not self.is_backtesting and len(self._trade_list) > self.TRADE_INSTANCE_LIMIT:
            self._trade_list.popleft()

        # add into trade list
        self._trade_list.append(cur_trade)

        if not self.is_backtesting:
            # log current trade
            self._log_trade(cur_trade)

            # log and initiate watcher for each order in current trade
            for order in cur_trade.orders:
                self._log_order(order)
                OrderWatcher(order).start()

    def add_switch_over(self, switch_over: SwitchOver):
        # pop the left-most element if the size has reached the set limit
        if not self.is_backtesting and len(self._switch_over_list) > self.SWITCH_OVER_INSTANCE_LIMIT:
            self._switch_over_list.popleft()
        self._switch_over_list.append(switch_over)

    def get_trade_count(self, target_trade_tag: TradeTag = None):
        if target_trade_tag is None:
            return len(self._trade_list)
        else:
            return sum(1 for trade in self._trade_list if trade.trade_tag is target_trade_tag)

    def clear_trade_count(self):
        self._trade_list.clear()

    def get_last_trade(self):
        return self._trade_list[-1] if len(self._trade_list) > 0 else None

    def get_last_switch_over(self):
        return self._switch_over_list[-1] if len(self._switch_over_list) > 0 else None

    def get_average_switch_over_spent_time(self):
        spent_time_list = [switch_over.get("spent_time") for switch_over in self._switch_over_list]
        return numpy.mean(spent_time_list) if len(spent_time_list) > 0 else 0

    def get_switch_over_count(self):
        return len(self._switch_over_list)

    def _log_trade(self, trade: Trade):
        logging.info("[TRADE RESULT]: ", trade)
        if self.should_db_logging:
            SharedMongoClient.async_trade_insert(trade.to_dict())

    def _log_order(self, order: Order):
        logging.info("[ORDER RESULT]:", order)
        if self.should_db_logging:
            SharedMongoClient.async_order_insert(order.to_dict())
