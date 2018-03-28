from .market_manager import MarketManager
from api.currency import CoinoneCurrency
from api.coinone_api import CoinoneApi
from trader.market.market import Market


class CoinoneMarketManager(MarketManager):
    MARKET_TAG = Market.COINONE
    MARKET_FEE = 0.001

    def __init__(self):
        super().__init__(self.MARKET_TAG, self.MARKET_FEE, CoinoneApi())

    @staticmethod
    def get_market_currency(target_currency: str):
        return CoinoneCurrency[target_currency.upper()]
