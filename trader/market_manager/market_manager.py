from abc import ABC, abstractmethod
from api.currency import Currency
from pymongo import MongoClient
from config.global_conf import Global
from trader.market.order import Order
from trader.market.balance import Balance
import logging


class MarketManager(ABC):
    def __init__(self, should_db_logging, market_fee):
        self.should_db_logging = should_db_logging
        self.market_fee = market_fee
        self.order_list = list()

        if self.should_db_logging:
            # init db related
            self.mongo_client = MongoClient(Global.read_mongodb_uri())
            target_db = self.mongo_client["bot_log"]
            self.order_col = target_db["order"]
            self.filled_order_col = target_db["filled_order"]
            self.balance_col = target_db["balance"]

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
        logging.info(order)
        if self.should_db_logging:
            self.order_col.insert_one(order.to_dict())

    def log_balance(self, balance: Balance):
        logging.info(balance)
        if self.should_db_logging:
            self.balance_col.insert_one(balance.to_dict())

    def calc_actual_coin_need_to_buy(self, amount):
        return amount / (1 - self.market_fee)
