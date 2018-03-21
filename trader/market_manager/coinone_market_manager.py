from .market_manager import MarketManager
from api.currency import CoinoneCurrency
from api.coinone_api import CoinoneApi


class CoinoneMarketManager(MarketManager):
    MARKET_FEE = 0.001

    def __init__(self):
        self.coinone_api = CoinoneApi()
        self.balance = None
        self.update_balance()
        self.order_list = list()

    def order_buy(self, currency: CoinoneCurrency, price: int, amount: float):
        res_json = self.coinone_api.order_limit_buy(currency, price, amount)
        order_id = res_json["orderId"]
        self.order_list.

    def order_sell(self, currency: CoinoneCurrency, price: int, amount: float):
        res_json = self.coinone_api.order_limit_sell(currency, price, amount)
        order_id = res_json["orderId"]

    def update_balance(self):
        self.balance = self.coinone_api.get_balance()

    def get_balance(self):
        return self.balance
