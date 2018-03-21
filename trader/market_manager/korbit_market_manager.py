from .market_manager import MarketManager
from api.currency import KorbitCurrency
from api.korbit_api import KorbitApi


class KorbitMarketManager(MarketManager):
    MARKET_FEE = 0.0008

    def __init__(self):
        self.korbit_api = KorbitApi()
        self.balance = None
        self.update_balance()

    def order_buy(self, currency: KorbitCurrency, price: int, amount: float):
        self.korbit_api.order_limit_buy(currency, price, amount)

    def order_sell(self, currency: KorbitCurrency, price: int, amount: float):
        self.korbit_api.order_limit_sell(currency, price, amount)

    def update_balance(self):
        self.balance = self.korbit_api.get_balance()

    def get_balance(self):
        return self.balance
