import time
import logging
from .order import Order, OrderStatus
from .market import Market
from threading import Thread
from api.coinone_api import CoinoneApi
from api.korbit_api import KorbitApi
from config.global_conf import Global


class OrderWatcher(Thread):
    supported_markets = {
        Market.COINONE: CoinoneApi,
        Market.KORBIT: KorbitApi
    }

    @staticmethod
    def is_watchable(order: Order):
        return order.market in OrderWatcher.supported_markets.keys()

    def __init__(self, order: Order, interval_sec: int, max_wait_sec: int):
        super().__init__()
        self.order = order
        self.interval_sec = interval_sec
        self.max_wait_sec = max_wait_sec
        self.api = self.supported_markets.get(self.order.market).instance()

    def do_interval(self):
        res_json = self.api.get_order_info(self.order.currency, self.order.order_id)
        self.order.update_from_api(res_json)
        # TODO: log intermediate order info onto different log file

    def run(self):
        # do nothing if the market is not watchable
        if not self.is_watchable(self.order):
            return

        # log initial time
        initial_time = time.time()
        is_aborted = False

        while self.order.status is not OrderStatus.FILLED:
            start_time = time.time()
            self.do_interval()
            end_time = time.time()

            # break if current time has exceeded the max_wait_sec
            time_check = end_time - initial_time
            if time_check > self.max_wait_sec:
                is_aborted = True
                break

            # wait for the target interval
            wait_time = self.interval_sec - (end_time - start_time)
            if wait_time > 0:
                time.sleep(wait_time)

        if is_aborted:
            # TODO: consider quiting entire process or cancelling the order => needs some measures anyways
            message = "Order %s has exceeded maximum wait time! OrderWatcher is now inactive! " \
                      "Counter measures are expected to be executed manually!" % self.order.order_id
            logging.critical(message)
            Global.send_to_slack_channel(message)

        if self.order.status is OrderStatus.FILLED:
            logging.info(self.order.get_filled_status())
