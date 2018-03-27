from .market_manager import MarketManager
from api.currency import KorbitCurrency
from api.korbit_api import KorbitApi
from trader.market.order import Order, OrderType, Market
from trader.market.balance import Balance
import logging


class KorbitMarketManager(MarketManager):
    MARKET_TAG = Market.KORBIT
    MARKET_FEE = 0.0008

    def __init__(self, should_db_logging=False):
        super().__init__(should_db_logging, self.MARKET_TAG, self.MARKET_FEE, Balance(self.MARKET_TAG))
        self.korbit_api = KorbitApi()
        self.update_balance()

    def order_buy(self, currency: KorbitCurrency, price: int, amount: float):
        actual_amount = round(self.calc_actual_coin_need_to_buy(amount), 4)
        if not self.has_enough_coin("krw", actual_amount * price):
            logging.error("[%s] Could not order_buy" % self.market_tag)
            return

        res_json = self.korbit_api.order_limit_buy(currency, price, actual_amount)
        logging.info(res_json)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_BUY, order_id, price, actual_amount)

        self.common_post_order_process(new_order)

    def order_sell(self, currency: KorbitCurrency, price: int, amount: float):
        if not self.has_enough_coin(currency.name.lower(), amount):
            logging.error("[%s] Could not order_sell" % self.market_tag)
            return

        res_json = self.korbit_api.order_limit_sell(currency, price, amount)
        logging.info(res_json)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_SELL, order_id, price, amount)

        self.common_post_order_process(new_order)

    def update_balance(self):
        self.balance.update(self.korbit_api.get_balance())

    def get_orderbook(self, currency: KorbitCurrency):
        return self.korbit_api.get_orderbook(currency)

    def get_ticker(self, currency: KorbitCurrency):
        return self.korbit_api.get_ticker(currency)

    @staticmethod
    def get_market_currency(target_currency: str):
        return KorbitCurrency[target_currency.upper()]
