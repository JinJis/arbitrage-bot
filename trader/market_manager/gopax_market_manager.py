from .market_manager import MarketManager
from api.currency import GopaxCurrency
from api.gopax_api import GopaxAPI
from trader.market.market import Market


class GopaxMarketManager(MarketManager):
    MARKET_TAG = Market.GOPAX
    MARKET_FEE = 0.00075

    def __init__(self):
        super().__init__(self.MARKET_TAG, self.MARKET_FEE, GopaxAPI.instance())

    @staticmethod
    def get_market_currency(target_currency: str) -> "GopaxCurrency":
        return GopaxCurrency[target_currency.upper()]
