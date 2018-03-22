from abc import ABC, abstractmethod
from api.currency import Currency
from pymongo import MongoClient
from config.global_conf import Global
from .order import Order


class MarketManager(ABC):
    def __init__(self):
        self.mongo_client = MongoClient(Global.read_mongodb_uri())
        target_db = self.mongo_client["bot_log"]
        self.order_col = target_db["order"]
        self.filled_order_col = target_db["filled_order"]

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

    def log_order(self, order: Order):
        self.order_col(order.to_dict())
