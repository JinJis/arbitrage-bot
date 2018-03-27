from abc import ABC, abstractmethod
from api.currency import Currency
from pymongo import MongoClient
from config.global_conf import Global
from trader.market.order import Order
from trader.market.balance import Balance
import logging
from trader.market.market import Market


class MarketManager(ABC):
    def __init__(self, should_db_logging: bool, market_tag: Market, market_fee: float, balance: Balance):
        self.should_db_logging = should_db_logging
        self.market_tag = market_tag
        self.market_fee = market_fee
        self.balance = balance
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

    def get_balance(self):
        return self.balance

    def log_order(self, order: Order):
        logging.info(order)
        if self.should_db_logging:
            self.order_col.insert_one(order.to_dict())

    def log_balance(self):
        logging.info(self.balance)
        if self.should_db_logging:
            self.balance_col.insert_one(self.balance.to_dict())

    def calc_actual_coin_need_to_buy(self, amount):
        return amount / (1 - self.market_fee)

    @abstractmethod
    def get_orderbook(self, currency: Currency):
        pass

    @abstractmethod
    def get_ticker(self, currency: Currency):
        pass

    def get_market_tag(self):
        return self.market_tag

    @staticmethod
    @abstractmethod
    def get_market_currency(target_currency: str):
        pass

    def has_enough_coin(self, coin_type: str, needed_amount: float):
        available_amount = self.balance.get_available_coin(coin_type)
        if available_amount < needed_amount:
            # log warning if balance is not enough
            logging.warning("[%s][Not enough %s balance] available: %d, needed: %d" %
                            (self.market_tag, coin_type.upper(), available_amount, needed_amount))
            return False
        else:
            return True

    def record_order(self, order: Order):
        # record order
        self.order_list.append(order)
        self.log_order(order)

        # record balance
        self.update_balance()
        self.log_balance()
