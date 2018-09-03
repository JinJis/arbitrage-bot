import logging
from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency
from trader.market.market import Market
from .market_manager import MarketManager


class CoinoneMarketManager(MarketManager):
    def __init__(self):
        try:
            super().__init__(Market.COINONE, CoinoneApi.instance())
        except ConnectionError:
            logging.error("Coinone API connection failed.. possible reason: API Maintenance")
            pass

    @staticmethod
    def get_market_currency(target_currency: str) -> "CoinoneCurrency":
        return CoinoneCurrency[target_currency.upper()]
