from .market_manager import MarketManager
from api.currency import Currency, CoinoneCurrency, KorbitCurrency, GopaxCurrency
from trader.market.order import Market
from api.coinone_api import CoinoneApi
from api.korbit_api import KorbitApi
from api.gopax_api import GopaxApi
from trader.market.order import Order, OrderType
from decimal import Decimal
from bson import Decimal128


class VirtualMarketManager(MarketManager):

    def __init__(self, market_tag: Market, market_fee: float, krw_balance=100000, coin_balance=0.1, coin_name="eth"):
        # create api instance according to given api_type
        if market_tag is Market.VIRTUAL_CO:
            target_api = CoinoneApi.instance(is_public_access_only=True)
            self.name = "co"
        elif market_tag is Market.VIRTUAL_KB:
            target_api = KorbitApi.instance(is_public_access_only=True)
            self.name = "kb"
        elif market_tag is Market.VIRTUAL_GP:
            target_api = GopaxApi.instance(is_public_access_only=True)
            self.name = "gp"
        else:
            raise Exception("Invalid market type has set for virtual market!")

        self.vt_balance = {
            "krw": krw_balance,
            coin_name: coin_balance
        }
        self.order_id_count = 0
        super().__init__(market_tag, market_fee, target_api)

        self.history = dict()

    def order_buy(self, currency: Currency, price: int, amount: float):
        if not self.has_enough_coin("krw", amount * price):
            raise Exception("[%s] Could not order_buy" % self.market_tag)

        self.vt_balance[currency.name.lower()] += amount * (1 - self.market_fee)
        self.vt_balance["krw"] -= amount * price
        try:
            self.history[price] -= amount
        except KeyError:
            self.history[price] = 0
            self.history[price] -= amount
        return Order(self.market_tag, currency, OrderType.LIMIT_BUY, self.generate_buy_order_id(), price, amount)

    def order_sell(self, currency: Currency, price: int, amount: float):
        if not self.has_enough_coin(currency.name.lower(), amount):
            raise Exception("[%s] Could not order_sell" % self.market_tag)

        self.vt_balance[currency.name.lower()] -= amount
        self.vt_balance["krw"] += price * amount * (1 - self.market_fee)
        try:
            self.history[price] += amount
        except KeyError:
            self.history[price] = 0
            self.history[price] += amount
        return Order(self.market_tag, currency, OrderType.LIMIT_SELL, self.generate_sell_order_id(), price, amount)

    def update_balance(self):
        balance_dict = dict()
        for key in self.vt_balance.keys():
            coin_bal = self.vt_balance[key]
            balance_dict[key] = {
                "available": coin_bal,
                "trade_in_use": 0,
                "balance": coin_bal
            }
        self.balance.update(balance_dict)

    # override static method
    def get_market_currency(self, target_currency: str) -> "Currency":
        if self.market_tag is Market.VIRTUAL_CO:
            return CoinoneCurrency[target_currency.upper()]
        elif self.market_tag is Market.VIRTUAL_KB:
            return KorbitCurrency[target_currency.upper()]
        elif self.market_tag is Market.VIRTUAL_GP:
            return GopaxCurrency[target_currency.upper()]
        else:
            raise Exception("Invalid target API type has set!")

    def _generate_order_id(self, tag: str):
        self.order_id_count += 1
        return "%s_%s_%s" % (self.name, tag, str(self.order_id_count))

    def generate_buy_order_id(self):
        return self._generate_order_id("buy")

    def generate_sell_order_id(self):
        return self._generate_order_id("sell")

    def apply_history_to_orderbook(self, orderbook: dict):
        history_keys = self.history.keys()
        for order in orderbook["asks"]:
            price = order["price"]
            if price in history_keys:
                order["amount"] = Decimal128(order["amount"].to_decimal() + Decimal(self.history[price]))
                if order["amount"].to_decimal() < 0:
                    order["amount"] = Decimal128("0")
        for order in orderbook["bids"]:
            price = order["price"]
            if price in history_keys:
                order["amount"] = Decimal128(order["amount"].to_decimal() - Decimal(self.history[price]))
                if order["amount"].to_decimal() < 0:
                    order["amount"] = Decimal128("0")
        return orderbook
