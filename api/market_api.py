import requests
from threading import Lock
from abc import ABC, abstractmethod
from .currency import Currency
from trader.market.order import Order


# implemented singleton for APIs
# since process of refreshing or writing the token
# should occur only in one instance & in a thread-safe way
# so handle it carefully using the `instance` method to retrieve the singleton instance
# especially when using the private api
class MarketApi(ABC):
    # note that parent's class variables are not shared, but instead are inherited onto child classes
    # so don't need worry about different implementations using the same variables
    __singleton_lock = Lock()
    __singleton_instance = None
    __singleton_creation_checked = False

    __singleton_lock_public = Lock()
    __singleton_instance_public = None
    __singleton_creation_checked_public = False

    # needed when refreshing the token in child classes
    __access_token_lock = Lock()

    @classmethod
    def instance(cls, is_public_access_only=False):
        # double-checked locking pattern to create singleton instance
        if not is_public_access_only:
            if not cls.__singleton_instance:
                with cls.__singleton_lock:
                    if not cls.__singleton_instance:
                        cls.__singleton_creation_checked = True
                        cls.__singleton_instance = cls()
            return cls.__singleton_instance
        else:
            if not cls.__singleton_instance_public:
                with cls.__singleton_lock_public:
                    if not cls.__singleton_instance_public:
                        cls.__singleton_creation_checked_public = True
                        cls.__singleton_instance_public = cls(is_public_access_only)
            return cls.__singleton_instance_public

    @abstractmethod
    def __init__(self, is_public_access_only=False):
        # Error case
        # 1) when the checked flag is not held to True
        # 2) when the singleton instance is already present
        if ((not is_public_access_only and not self.__singleton_creation_checked) or
                (not is_public_access_only and self.__singleton_instance is not None) or
                (is_public_access_only and not self.__singleton_creation_checked_public) or
                (is_public_access_only and self.__singleton_instance_public is not None)):
            raise Exception("You should not create MarketApi instance on your own "
                            "when using private API! Please use `instance` method in order "
                            "to get the global singleton instance. This is to prevent "
                            "the collision while handling the access token.")
        else:
            # initiate instance attribute session
            # this is to reuse TCP connection, and avoid DNS errors
            self._session = requests.Session()
        pass

    # public api

    @abstractmethod
    def get_ticker(self, currency: Currency):
        pass

    @abstractmethod
    def get_orderbook(self, currency: Currency):
        pass

    @abstractmethod
    def get_filled_orders(self, currency: Currency, time_range: str):
        pass

    # private api

    @abstractmethod
    def get_balance(self):
        pass

    @abstractmethod
    def order_limit_buy(self, currency: Currency, price: int, amount: float):
        pass

    @abstractmethod
    def order_limit_sell(self, currency: Currency, price: int, amount: float):
        pass

    @abstractmethod
    def cancel_order(self, currency: Currency, order: Order):
        pass

    @abstractmethod
    def get_order_info(self, currency: Currency, order: Order):
        pass

    # 미체결 주문 내역
    @abstractmethod
    def get_open_orders(self, currency: Currency):
        pass

    # 체결 주문 내역
    @abstractmethod
    def get_past_trades(self, currency: Currency):
        pass

    @staticmethod
    def
