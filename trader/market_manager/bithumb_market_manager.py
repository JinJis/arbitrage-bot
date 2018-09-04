from .market_manager import MarketManager
from api.currency import BithumbCurrency
from api.bithumb_api import BithumbApi
from trader.market.market import Market


class BithumbMarketManager(MarketManager):
    def __init__(self):
        super().__init__(Market.BITHUMB, BithumbApi.instance())

    @staticmethod
    def get_market_currency(target_currency: str) -> "BithumbCurrency":
        return BithumbCurrency[target_currency.upper()]
