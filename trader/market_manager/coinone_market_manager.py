from .market_manager import MarketManager
from api.currency import CoinoneCurrency
from api.coinone_api import CoinoneApi
from trader.market.order import Order, OrderType, Market
from trader.market.balance import Balance
import logging


class CoinoneMarketManager(MarketManager):
    MARKET_TAG = Market.COINONE
    MARKET_FEE = 0.001

    def __init__(self):
        super().__init__(self.MARKET_TAG, self.MARKET_FEE, Balance(self.MARKET_TAG))
        self.coinone_api = CoinoneApi()
        # Note that updating balance is already included in initialization phase
        self.update_balance()

    def order_buy(self, currency: CoinoneCurrency, price: int, amount: float):
        actual_amount = round(self.calc_actual_coin_need_to_buy(amount), 4)
        if not self.has_enough_coin("krw", actual_amount * price):
            raise Exception("[%s] Could not order_buy" % self.market_tag)

        res_json = self.coinone_api.order_limit_buy(currency, price, actual_amount)
        logging.info(res_json)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_BUY, order_id, price, actual_amount)
        return new_order

    def order_sell(self, currency: CoinoneCurrency, price: int, amount: float):
        if not self.has_enough_coin(currency.name.lower(), amount):
            raise Exception("[%s] Could not order_sell" % self.market_tag)

        res_json = self.coinone_api.order_limit_sell(currency, price, amount)
        logging.info(res_json)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_SELL, order_id, price, amount)
        return new_order

    def update_balance(self):
        self.balance.update(self.coinone_api.get_balance())

    def get_orderbook(self, currency: CoinoneCurrency):
        return self.coinone_api.get_orderbook(currency)

    def get_ticker(self, currency: CoinoneCurrency):
        return self.coinone_api.get_ticker(currency)

    @staticmethod
    def get_market_currency(target_currency: str):
        return CoinoneCurrency[target_currency.upper()]
