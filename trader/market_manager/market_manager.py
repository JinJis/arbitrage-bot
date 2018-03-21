from abc import ABC, abstractmethod
from api.currency import Currency


class MarketManager(ABC):
    @abstractmethod
    def order_buy(self, currency: Currency, price: int, amount: float):
        pass

    @abstractmethod
    def order_sell(self, currency: Currency, price: int, amount: float):
        pass

    @abstractmethod
    def update_balance(self):
        pass

    @abstractmethod
    def get_balance(self):
        pass
