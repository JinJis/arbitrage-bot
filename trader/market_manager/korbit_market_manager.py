from api.currency import KorbitCurrency
from api.korbit_api import KorbitApi
from trader.market.market import Market
from .market_manager import MarketManager


class KorbitMarketManager(MarketManager):
    def __init__(self):
        super().__init__(Market.KORBIT, KorbitApi.instance())

    @staticmethod
    def get_market_currency(target_currency: str) -> "KorbitCurrency":
        return KorbitCurrency[target_currency.upper()]
