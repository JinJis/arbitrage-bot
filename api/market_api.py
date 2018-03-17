from abc import ABC, abstractmethod
from .currency import Currency


class MarketApi(ABC):

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
    def order_buy(self, currency: Currency, price: int, amount: float, order_type: str):
        pass

    @abstractmethod
    def order_sell(self, currency: Currency, price: int, amount: float, order_type: str):
        pass

    @abstractmethod
    def cancel_order(self, currency: Currency, price: int, amount: float, order_type: str, order_id: int):
        pass
