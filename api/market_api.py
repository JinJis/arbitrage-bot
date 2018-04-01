import logging
import threading
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
    __singleton_lock = threading.Lock()
    __singleton_lock_public = threading.Lock()
    __singleton_instance = None
    __singleton_instance_public = None
    __singleton_creation_checked = False

    @classmethod
    def instance(cls, is_public_access_only=False):
        # double-checked locking pattern to create singleton instance
        if not is_public_access_only:
            if not cls.__singleton_instance:
                with cls.__singleton_lock:
                    if not cls.__singleton_instance:
                        cls.__singleton_creation_checked = True
                        cls.__singleton_instance = cls()
        else:
            if not cls.__singleton_instance_public:
                with cls.__singleton_lock_public:
                    if not cls.__singleton_instance_public:
                        cls.__singleton_instance_public = cls(is_public_access_only)

    @abstractmethod
    def __init__(self, is_public_access_only=False):
        # Error case
        # 1) when it's not notated as public_access_only use, and the checked flag is not held to True
        # 2) when the singleton instance is already present
        if ((not is_public_access_only and not self.__singleton_creation_checked) or
                (self.__singleton_instance is not None)):
            raise Exception("You should not create MarketApi instance on your own "
                            "when using private API! Please use `instance` method in order "
                            "to get the global singleton instance. This is to prevent "
                            "the collision while handling the access token.")
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
    def get_order_info(self, currency: Currency, order_id: str):
        pass

    @abstractmethod
    def get_open_orders(self, currency: Currency):
        pass

    @abstractmethod
    def get_past_trades(self, currency: Currency):
        pass
