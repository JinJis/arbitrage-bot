from config.global_conf import Global
from .market_manager import MarketManager
from api.currency import CoinnestCurrency
from api.coinnest_api import CoinnestApi
from trader.market.market import Market


class CoinnestMarketManager(MarketManager):
    MARKET_TAG = Market.COINNEST
    TAKER_FEE = Global.read_market_fee(market_name="coinnest", is_taker_fee=True)
    MAKER_FEE = Global.read_market_fee(market_name="coinnest", is_taker_fee=False)

    def __init__(self, is_using_taker_fee: bool):
        super().__init__(self.MARKET_TAG, self.TAKER_FEE, self.MAKER_FEE, CoinnestApi.instance(), is_using_taker_fee)

    @staticmethod
    def get_market_currency(target_currency: str) -> "CoinnestCurrency":
        return CoinnestCurrency[target_currency.upper()]
