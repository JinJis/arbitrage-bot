import logging
import time
from threading import Thread
from api.bithumb_api import BithumbApi
from api.coinnest_api import CoinnestApi
from api.coinone_api import CoinoneApi
from api.coinone_error import CoinoneError
from api.gopax_api import GopaxApi
from api.korbit_api import KorbitApi
from api.okcoin_api import OkcoinApi
from api.okcoin_error import OkcoinError
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from trader.market.market import Market
from trader.market.order import Order, OrderStatus
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator
from trader.market_manager.gopax_market_manager import GopaxMarketManager
from .order_watcher_stats import OrderWatcherStats


class OrderWatcher(Thread):
    TARGET_INTERVAL_SEC = 10
    DELAYED_FLAG_SEC = 60 * 15

    supported_markets = {
        Market.COINONE: CoinoneApi,
        Market.KORBIT: KorbitApi,
        Market.GOPAX: GopaxApi,
        Market.BITHUMB: BithumbApi,
        Market.OKCOIN: OkcoinApi,
        Market.COINNEST: CoinnestApi
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
            res_json = self.api.get_order_info(self.order.currency, self.order)
            if res_json is None:
                # it's impossible to know if a gopax order is cancelled or not
                # this behavior may need to be changed in accordance with the api changes
                if self.order.market is Market.GOPAX:
                    # gopax api sucks, just consider it done (or cancelled)
                    # see `get_order_info` method for detail
                    self.order.updated_at = int(time.time())
                    self.order.filled_amount = self.order.order_amount
                    self.order.remain_amount = 0
                    self.order.fee_rate = GopaxMarketManager().taker_fee
                    self.order.fee = self.order.fee_rate * self.order.filled_amount
                    self.order.status = OrderStatus.FILLED
                else:
                    raise Exception("Unexpected response: with `get_order_info`, returned None")
            else:
                self.order.update_from_api(res_json)
        except KorbitApi as e:
            # consider it cancelled
            if "Order id does not exist" in str(e):
                logging.info("Order<%s> in %s is cancelled." % (self.order.order_id, self.order.market.value))
                self.order.status = OrderStatus.CANCELLED
            else:
                logging.warning(e)
                logging.warning("get_order_info in OrderWatcher failed! (Order %s)" % self.order.order_id)
        except CoinoneError as e:
            # consider it cancelled
            if "Order id does not exist" in str(e):
                logging.info("Order<%s> in %s is cancelled." % (self.order.order_id, self.order.market.value))
                self.order.status = OrderStatus.CANCELLED
            else:
                logging.warning(e)
                logging.warning("get_order_info in OrderWatcher failed! (Order %s)" % self.order.order_id)
        except OkcoinError as e:
            # consider it cancelled
            if "Order id does not exist" in str(e):
                logging.info("Order<%s> in %s is cancelled." % (self.order.order_id, self.order.market.value))
                self.order.status = OrderStatus.CANCELLED
            else:
                logging.warning(e)
                logging.warning("get_order_info in OrderWatcher failed! (Order %s)" % self.order.order_id)
        except Exception as e:
            logging.warning(e)
            logging.warning("get_order_info in OrderWatcher failed! (Order %s)" % self.order.order_id)
        finally:
            SharedMongoClient.async_order_insert(self.order.to_dict())

    def run(self):
        # do nothing if the market of order is not watchable
        if not self.is_watchable(self.order):
            return

        # add in order watcher stats
        OrderWatcherStats.started(self.order.order_id)

        # log initial time
        initial_time = time.time()

        try:
            while (self.order.status is not OrderStatus.FILLED) and (self.order.status is not OrderStatus.CANCELLED):
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
                # if sell, krw as fee
                # if buy, coin as fee
                if self.order.is_sell_order():
                    GlobalFeeAccumulator.add_fee_expenditure(self.order.market, "krw", self.order.fee)
                else:
                    GlobalFeeAccumulator.add_fee_expenditure(self.order.market, self.order.currency.name.lower(),
                                                             self.order.fee)
            elif self.order.status is OrderStatus.CANCELLED:
                OrderWatcherStats.cancelled(self.order.order_id)

        except Exception as e:
            # if there was any error for some unexpected reasons
            OrderWatcherStats.error(self.order.order_id)
            logging.error(e)
            # thread will be terminated after this
