from .order import Order
from .market import Market
from threading import Thread
from api.coinone_api import CoinoneApi
from api.korbit_api import KorbitApi


class OrderWatcher(Thread):
    supported_markets = (Market.COINONE, Market.KORBIT)

    @staticmethod
    def is_watchable(order: Order):
        return order.market in OrderWatcher.supported_markets

    def __init__(self, order: Order):
        super().__init__()
        self.order = order

        if self.order.market is Market.COINONE:
            self.api = CoinoneApi.instance()
        elif self.order.market is Market.KORBIT:
            self.api = KorbitApi.instance()

    def run(self):
        if not self.is_watchable(self.order):
            return
