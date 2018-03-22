from .market_manager import MarketManager
from api.currency import Currency
from trader.market.order import Market


class VirtualMarketManager(MarketManager):
    MARKET_TAG = Market.VIRTUAL

    def __init__(self, name, market_fee=0.001, krw_balance=100000, eth_balance=0.1, should_db_logging=False):
        super().__init__(should_db_logging, market_fee)
        self.name = name
        self.krw_balance = krw_balance
        self.eth_balance = eth_balance

    def order_buy(self, currency: Currency, price: int, amount: float):
        self.eth_balance += amount
        self.krw_balance -= price * (amount / (1 - self.market_fee))

    def order_sell(self, currency: Currency, price: int, amount: float):
        self.eth_balance -= amount
        self.krw_balance += price * amount * (1 - self.market_fee)

    def update_balance(self):
        pass

    def get_balance(self):
        return {
            "krw": self.krw_balance,
            "eth": self.eth_balance
        }
