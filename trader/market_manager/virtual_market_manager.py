from .market_manager import MarketManager
from api.currency import VirtualCurrency, KorbitCurrency, CoinoneCurrency
from trader.market.order import Market
from trader.market.balance import Balance
from decimal import Decimal
from enum import Enum
from api.coinone_api import CoinoneApi
from api.korbit_api import KorbitApi
import logging
from trader.market.order import Order, OrderType


class VirtualMarketApiType(Enum):
    COINONE = "coinone"
    KORBIT = "korbit"


class VirtualMarketManager(MarketManager):
    MARKET_TAG = Market.VIRTUAL

    def __init__(self, name: str, api_type: VirtualMarketApiType, market_fee=0.001,
                 krw_balance=100000, eth_balance=0.1, should_db_logging=False):
        super().__init__(should_db_logging, self.MARKET_TAG, market_fee, Balance(self.MARKET_TAG))
        self.name = name
        self.api_type = api_type
        self.krw_balance = krw_balance
        self.eth_balance = eth_balance
        self.update_balance()
        self.order_id_count = 0

        if self.api_type is VirtualMarketApiType.COINONE:
            self.api = CoinoneApi(is_public_access_only=True)
        elif self.api_type is VirtualMarketApiType.KORBIT:
            self.api = KorbitApi(is_public_access_only=True)
        else:
            raise Exception("Invalid target API type has set!")

    def order_buy(self, currency: VirtualCurrency, price: int, amount: float):
        actual_amount = self.calc_actual_coin_need_to_buy(amount)
        if not self.has_enough_coin("krw", actual_amount * price):
            logging.error("[%s] Could not order_buy" % self.market_tag)
            return

        self.eth_balance += amount
        self.krw_balance -= price * actual_amount
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_BUY, self.generate_order_id(), price, actual_amount)

        self.common_post_order_process(new_order)

    def order_sell(self, currency: VirtualCurrency, price: int, amount: float):
        if not self.has_enough_coin(currency.name.lower(), amount):
            logging.error("[%s] Could not order_sell" % self.market_tag)
            return

        self.eth_balance -= amount
        self.krw_balance += price * amount * (1 - self.market_fee)
        new_order = Order(self.MARKET_TAG, OrderType.LIMIT_SELL, self.generate_order_id(), price, amount)

        self.common_post_order_process(new_order)

    def update_balance(self):
        eth_bal = Decimal(self.eth_balance)
        krw_bal = Decimal(self.krw_balance)
        zero = Decimal(0)
        self.balance.update({
            "eth": {
                "available": eth_bal,
                "trade_in_use": zero,
                "balance": eth_bal
            },
            "krw": {
                "available": krw_bal,
                "trade_in_use": zero,
                "balance": krw_bal
            }
        })

    def get_orderbook(self, currency: VirtualCurrency):
        target_api_currency = self._convert_to_target_api_currency(currency)
        return self.api.get_orderbook(target_api_currency)

    def get_ticker(self, currency: VirtualCurrency):
        target_api_currency = self._convert_to_target_api_currency(currency)
        return self.api.get_ticker(target_api_currency)

    @staticmethod
    def get_market_currency(target_currency: str):
        return VirtualCurrency[target_currency.upper()]

    def _convert_to_target_api_currency(self, currency: VirtualCurrency):
        if self.api_type is VirtualMarketApiType.COINONE:
            return CoinoneCurrency[currency.name]
        elif self.api_type is VirtualMarketApiType.KORBIT:
            return KorbitCurrency[currency.name]
        else:
            raise Exception("Invalid target API type has set!")

    def generate_order_id(self):
        self.order_id_count += 1
        return str(self.order_id_count)
