from .market_manager import MarketManager
from api.currency import CoinoneCurrency
from api.coinone_api import CoinoneApi
from trader.market.order import Order, OrderType, Market
from trader.market.balance import Balance


class CoinoneMarketManager(MarketManager):
    MARKET_TAG = Market.COINONE
    MARKET_FEE = 0.001

    def __init__(self, should_db_logging=False):
        super().__init__(should_db_logging, self.MARKET_TAG, self.MARKET_FEE)
        self.coinone_api = CoinoneApi()
        self.balance = Balance(self.MARKET_TAG)
        self.update_balance()

    def order_buy(self, currency: CoinoneCurrency, price: int, amount: float):
        actual_amount = self.calc_actual_coin_need_to_buy(amount)
        res_json = self.coinone_api.order_limit_buy(currency, price, actual_amount)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_BUY, order_id, price, actual_amount)
        self.record_order(new_order)

    def order_sell(self, currency: CoinoneCurrency, price: int, amount: float):
        res_json = self.coinone_api.order_limit_sell(currency, price, amount)
        order_id = res_json["orderId"]
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_SELL, order_id, price, amount)
        self.record_order(new_order)

    def update_balance(self):
        self.balance.update(self.coinone_api.get_balance())

    def get_balance(self):
        return self.balance

    def record_order(self, order: Order):
        # record order
        self.order_list.append(order)
        self.log_order(order)

        # record balance
        self.update_balance()
        self.log_balance(self.balance)

    def get_orderbook(self, currency: CoinoneCurrency):
        return self.coinone_api.get_orderbook(currency)
