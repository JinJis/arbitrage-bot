from api.currency import GopaxCurrency
from api.gopax_api import GopaxApi
from trader.market.market import Market
from .market_manager import MarketManager


class GopaxMarketManager(MarketManager):
    def __init__(self):
        super().__init__(Market.GOPAX, GopaxApi.instance())

    @staticmethod
    def get_market_currency(target_currency: str) -> "GopaxCurrency":
        return GopaxCurrency[target_currency.upper()]
