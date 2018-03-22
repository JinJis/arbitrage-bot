from .market_manager import MarketManager
from api.currency import KorbitCurrency
from api.korbit_api import KorbitApi
from trader.market.order import Order, OrderType, Market
from trader.market.balance import Balance


class KorbitMarketManager(MarketManager):
    MARKET_TAG = Market.KORBIT
    MARKET_FEE = 0.0008

    def __init__(self, should_db_logging=False):
        super().__init__(should_db_logging, self.MARKET_FEE)
        self.korbit_api = KorbitApi()
        self.balance = Balance(self.MARKET_TAG)
        self.update_balance()

    def order_buy(self, currency: KorbitCurrency, price: int, amount: float):
        actual_amount = self.calc_actual_coin_need_to_buy(amount)
        res_json = self.korbit_api.order_limit_buy(currency, price, actual_amount)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_BUY, order_id, price, actual_amount)
        self.record_order(new_order)

    def order_sell(self, currency: KorbitCurrency, price: int, amount: float):
        res_json = self.korbit_api.order_limit_sell(currency, price, amount)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_SELL, order_id, price, amount)
        self.record_order(new_order)

    def update_balance(self):
        self.balance.update(self.korbit_api.get_balance())

    def get_balance(self):
        return self.balance

    def record_order(self, order: Order):
        # record order
        self.order_list.append(order)
        self.log_order(order)

        # record balance
        self.update_balance()
        self.log_balance(self.balance)
