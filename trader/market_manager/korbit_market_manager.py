from .market_manager import MarketManager
from api.currency import KorbitCurrency
from api.korbit_api import KorbitApi
from trader.market.market import Market


class KorbitMarketManager(MarketManager):
    MARKET_TAG = Market.KORBIT
    MARKET_FEE = 0.0008

    def __init__(self):
        super().__init__(self.MARKET_TAG, self.MARKET_FEE, KorbitApi.instance())

    @staticmethod
    def get_market_currency(target_currency: str):
        return KorbitCurrency[target_currency.upper()]
