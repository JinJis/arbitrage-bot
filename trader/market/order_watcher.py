import time
import logging
from .order import Order
from .market import Market
from threading import Thread
from config.global_conf import Global
from api.coinone_api import CoinoneApi
from api.korbit_api import KorbitApi


class OrderWatcher(Thread):
    supported_markets = (Market.COINONE, Market.KORBIT)

    @staticmethod
    def is_watchable(order: Order):
        return order.market in OrderWatcher.supported_markets

    def __init__(self, order: Order, interval_sec: int, max_wait_sec: int):
        super().__init__()
        self.order = order
        self.interval_sec = interval_sec
        self.max_wait_sec = max_wait_sec
        self.time_count = 0

        if self.order.market is Market.COINONE:
            self.api = CoinoneApi.instance()
        elif self.order.market is Market.KORBIT:
            self.api = KorbitApi.instance()

    def do_interval(self):
        logging.info("yo, i'm called")
        result = self.api.get_order_info(self.order.currency, self.order.order_id)
        # self.order.update

        # "status": order_info["status"],
        # "avg_filled_price": int(float(order_info["avg_price"])),
        # "order_amount": order_amount,
        # "filled_amount": filled_amount,
        # "remain_amount": order_amount - filled_amount,
        # "fee": float(fee) if fee is not None else 0

    def run(self):
        # do nothing if its market is not watchable
        if not self.is_watchable(self.order):
            return

        while not self.order.is_filled:
            start_time = time.time()
            self.do_interval()
            end_time = time.time()
            wait_time = self.interval_sec - (end_time - start_time)
            if wait_time > 0:
                time.sleep(wait_time)
