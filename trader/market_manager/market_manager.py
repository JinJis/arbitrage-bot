from abc import ABC, abstractmethod
from api.currency import Currency
from trader.market.balance import Balance
import logging
from trader.market.market import Market


class MarketManager(ABC):
    def __init__(self, market_tag: Market, market_fee: float, balance: Balance):
        self.market_tag = market_tag
        self.market_fee = market_fee
        self.balance = balance

    @abstractmethod
    def order_buy(self, currency: Currency, price: int, amount: float):
        pass

    @abstractmethod
    def order_sell(self, currency: Currency, price: int, amount: float):
        pass

    @abstractmethod
    def update_balance(self):
        pass

    def get_balance(self):
        return self.balance

    def calc_actual_coin_need_to_buy(self, amount):
        return amount / (1 - self.market_fee)

    @abstractmethod
    def get_orderbook(self, currency: Currency):
        pass

    @abstractmethod
    def get_ticker(self, currency: Currency):
        pass

    def get_market_name(self):
        return self.market_tag.value

    @staticmethod
    @abstractmethod
    def get_market_currency(target_currency: str):
        pass

    def has_enough_coin(self, coin_type: str, needed_amount: float):
        available_amount = self.balance.get_available_coin(coin_type.lower())
        if available_amount < needed_amount:
            # log warning if balance is not enough
            logging.warning("[%s][Not enough %s balance] available: %.4f, needed: %.4f" %
                            (self.market_tag, coin_type.upper(), available_amount, needed_amount))
            return False
        else:
            return True
