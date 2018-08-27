from api.coinnest_api import CoinnestApi
from api.currency import CoinnestCurrency
from trader.market.market import Market
from .market_manager import MarketManager


class CoinnestMarketManager(MarketManager):
    def __init__(self):
        super().__init__(Market.COINNEST, CoinnestApi.instance())

    @staticmethod
    def get_market_currency(target_currency: str) -> "CoinnestCurrency":
        return CoinnestCurrency[target_currency.upper()]
