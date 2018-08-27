from config.global_conf import Global
from .market_manager import MarketManager
from api.currency import BithumbCurrency
from api.bithumb_api import BithumbApi
from trader.market.market import Market


class BithumbMarketManager(MarketManager):
    MARKET_TAG = Market.BITHUMB
    TAKER_FEE = Global.read_market_fee(exchange_name="bithumb", is_taker_fee=True)
    MAKER_FEE = Global.read_market_fee(exchange_name="bithumb", is_taker_fee=False)

    def __init__(self, is_using_taker_fee: bool):
        super().__init__(self.MARKET_TAG, self.TAKER_FEE, self.MAKER_FEE, BithumbApi.instance(), is_using_taker_fee)

    @staticmethod
    def get_market_currency(target_currency: str) -> "BithumbCurrency":
        return BithumbCurrency[target_currency.upper()]
