import logging
from api.currency import OkcoinCurrency
from api.okcoin_api import OkcoinApi
from trader.market.market import Market
from .market_manager import MarketManager


class OkcoinMarketManager(MarketManager):
    def __init__(self):
        try:
            super().__init__(Market.OKCOIN, OkcoinApi.instance())
        except ConnectionError:
            logging.error("Okcoin API connection failed.. possible reason: API Maintenance")
            pass

    @staticmethod
    def get_market_currency(target_currency: str) -> "OkcoinCurrency":
        return OkcoinCurrency[target_currency.upper()]
