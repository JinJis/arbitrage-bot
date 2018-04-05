import time
import logging
from trader.market.order import Order, OrderStatus
from trader.market.market import Market
from threading import Thread
from api.coinone_api import CoinoneApi
from api.korbit_api import KorbitApi
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from .order_watcher_stats import OrderWatcherStats


class OrderWatcher(Thread):
    TARGET_INTERVAL_SEC = 5
    DELAYED_FLAG_SEC = 60 * 5

    supported_markets = {
        Market.COINONE: CoinoneApi,
        Market.KORBIT: KorbitApi
    }

    @staticmethod
    def is_watchable(order: Order):
        return order.market in OrderWatcher.supported_markets.keys()

    def __init__(self, order: Order):
        super().__init__()
        self.order = order
        self.interval_sec = OrderWatcher.TARGET_INTERVAL_SEC
        self.delayed_flag_sec = OrderWatcher.DELAYED_FLAG_SEC
        self.is_delayed = False

        # find matching api
        matched_api = self.supported_markets.get(self.order.market)
        if matched_api is not None:
            self.api = matched_api.instance()

    def do_interval(self):
        # noinspection PyBroadException
        try:
            res_json = self.api.get_order_info(self.order.currency, self.order.order_id)
            self.order.update_from_api(res_json)
        except Exception as e:
            logging.warning(e)
            logging.warning("get_order_info in OrderWatcher failed! (Order %s)" % self.order.order_id)
        finally:
            SharedMongoClient.async_order_update(self.order.to_dict())

    def run(self):
        # do nothing if the market of order is not watchable
        if not self.is_watchable(self.order):
            return

        # add in order watcher stats
        OrderWatcherStats.started(self.order.order_id)

        # log initial time
        initial_time = time.time()

        try:
            while self.order.status is not OrderStatus.FILLED:
                start_time = time.time()
                self.do_interval()
                end_time = time.time()

                # if current time has exceeded the max_wait_sec
                if not self.is_delayed:
                    time_check = end_time - initial_time
                    if time_check > self.delayed_flag_sec:
                        self.is_delayed = True
                        OrderWatcherStats.delayed(self.order.order_id)
                        message = "Order %s has exceeded delayed flag time! " \
                                  "Counter measures are expected to be executed manually!" % self.order.order_id
                        logging.critical(message)
                        Global.send_to_slack_channel(message)

                # wait for the target interval
                wait_time = self.interval_sec - (end_time - start_time)
                if wait_time > 0:
                    time.sleep(wait_time)

            # if it is filled
            if self.order.status is OrderStatus.FILLED:
                OrderWatcherStats.done(self.order.order_id)
                # logging.info(self.order.get_filled_status())

        except Exception as e:
            # if there was any error for some unexpected reasons
            OrderWatcherStats.error(self.order.order_id)
            logging.error(e)
