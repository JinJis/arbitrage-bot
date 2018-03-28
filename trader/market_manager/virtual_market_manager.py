from .market_manager import MarketManager
from api.currency import Currency, CoinoneCurrency, KorbitCurrency
from trader.market.order import Market
from decimal import Decimal
from enum import Enum
from api.coinone_api import CoinoneApi
from api.korbit_api import KorbitApi
from trader.market.order import Order, OrderType


class VirtualMarketApiType(Enum):
    COINONE = "coinone"
    KORBIT = "korbit"


class VirtualMarketManager(MarketManager):
    MARKET_TAG = Market.VIRTUAL

    def __init__(self, name: str, api_type: VirtualMarketApiType, market_fee, krw_balance=100000, eth_balance=0.1):
        # create api instance according to given api_type
        if api_type is VirtualMarketApiType.COINONE:
            target_api = CoinoneApi(is_public_access_only=True)
        elif api_type is VirtualMarketApiType.KORBIT:
            target_api = KorbitApi(is_public_access_only=True)
        else:
            raise Exception("Invalid target API type has set!")

        super().__init__(self.MARKET_TAG, market_fee, target_api)
        self.name = name
        self.api_type = api_type
        self.vt_balance = {
            "krw": krw_balance,
            "eth": eth_balance
        }
        self.order_id_count = 0

    def order_buy(self, currency: Currency, price: int, amount: float):
        actual_amount = self.calc_actual_coin_need_to_buy(amount)
        if not self.has_enough_coin("krw", actual_amount * price):
            raise Exception("[%s] Could not order_buy" % self.market_tag)

        self.vt_balance[currency.name.lower()] += amount
        self.vt_balance["krw"] -= price * actual_amount
        return Order(self.MARKET_TAG, OrderType.LIMIT_BUY, self.generate_order_id(), price, actual_amount)

    def order_sell(self, currency: Currency, price: int, amount: float):
        if not self.has_enough_coin(currency.name.lower(), amount):
            raise Exception("[%s] Could not order_sell" % self.market_tag)

        self.vt_balance[currency.name.lower()] -= amount
        self.vt_balance["krw"] += price * amount * (1 - self.market_fee)
        return Order(self.MARKET_TAG, OrderType.LIMIT_SELL, self.generate_order_id(), price, amount)

    def update_balance(self):
        zero = Decimal(0)
        balance_dict = dict()
        for key in self.vt_balance.keys():
            coin_bal = Decimal(self.vt_balance[key])
            balance_dict[key] = {
                "available": coin_bal,
                "trade_in_use": zero,
                "balance": coin_bal
            }
        self.balance.update(balance_dict)

    # override static method
    def get_market_currency(self, target_currency: str):
        if self.api_type is VirtualMarketApiType.COINONE:
            return CoinoneCurrency[target_currency.upper()]
        elif self.api_type is VirtualMarketApiType.KORBIT:
            return KorbitCurrency[target_currency.upper()]
        else:
            raise Exception("Invalid target API type has set!")

    def generate_order_id(self):
        self.order_id_count += 1
        return str(self.order_id_count)

    def get_market_name(self):
        return "%s_%s" % (self.market_tag.value, self.name)
