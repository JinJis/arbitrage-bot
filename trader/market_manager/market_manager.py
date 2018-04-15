import logging
from api.currency import Currency
from abc import ABC, abstractmethod
from api.market_api import MarketApi
from trader.market.market import Market
from trader.market.balance import Balance
from trader.market.order import Order, OrderType
from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator


class MarketManager(ABC):
    def __init__(self, market_tag: Market, market_fee: float, market_api: MarketApi):
        self.market_tag = market_tag
        self.market_fee = market_fee
        self.market_api = market_api

        # init fee accumulator
        GlobalFeeAccumulator.initialize_market(self.market_tag)

        # Note that updating balance is already included in initialization phase
        self.balance = Balance(self.get_market_name())
        self.update_balance()

    def get_market_tag(self):
        return self.market_tag

    def get_market_name(self):
        return str(self.market_tag.value)

    def order_buy(self, currency: Currency, price: int, amount: float):
        if not self.has_enough_coin("krw", amount * price):
            raise Exception("[%s] Could not order_buy" % self.get_market_name())

        res_json = self.market_api.order_limit_buy(currency, price, amount)
        logging.info(res_json)
        order_id = res_json["orderId"]
        new_order = Order(self.market_tag, currency, OrderType.LIMIT_BUY, order_id, price, amount)
        return new_order

    def order_sell(self, currency: Currency, price: int, amount: float):
        if not self.has_enough_coin(currency.name.lower(), amount):
            raise Exception("[%s] Could not order_sell" % self.get_market_name())

        res_json = self.market_api.order_limit_sell(currency, price, amount)
        logging.info(res_json)
        order_id = res_json["orderId"]
        new_order = Order(self.market_tag, currency, OrderType.LIMIT_SELL, order_id, price, amount)
        return new_order

    def get_orderbook(self, currency: Currency):
        return self.market_api.get_orderbook(currency)

    def get_ticker(self, currency: Currency):
        return self.market_api.get_ticker(currency)

    def update_balance(self):
        self.balance.update(self.market_api.get_balance())

    def get_balance(self):
        return self.balance

    def calc_actual_coin_need_to_buy(self, amount):
        return amount / (1 - self.market_fee)

    def has_enough_coin(self, coin_type: str, needed_amount: float):
        available_amount = self.balance.get_available_coin(coin_type.lower())
        if available_amount < needed_amount:
            # log warning if balance is not enough
            logging.info("[%s][Not enough %s balance] available: %.4f, needed: %.4f" %
                         (self.market_tag, coin_type.upper(), available_amount, needed_amount))
            return False
        else:
            return True

    def cancel_order(self, currency: Currency, order: Order):
        return self.market_api.cancel_order(currency, order)

    @staticmethod
    @abstractmethod
    def get_market_currency(target_currency: str) -> "Currency":
        pass

    def db_log_balance(self, timestamp: int):
        balance_dic = self.get_balance().to_dict()
        balance_dic["timestamp"] = timestamp
        SharedMongoClient.async_balance_insert(balance_dic)
