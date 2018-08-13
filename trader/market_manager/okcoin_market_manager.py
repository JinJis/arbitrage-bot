from config.global_conf import Global
from .market_manager import MarketManager
from api.currency import OkcoinCurrency
from api.okcoin_api import OkcoinApi
from trader.market.market import Market


class OkcoinMarketManager(MarketManager):
    MARKET_TAG = Market.OKCOIN
    TAKER_FEE = Global.read_market_fee(market_name="okcoin", is_taker_fee=True)
    MAKER_FEE = Global.read_market_fee(market_name="okcoin", is_taker_fee=False)

    def __init__(self, is_using_taker_fee: bool):
        super().__init__(self.MARKET_TAG, self.TAKER_FEE, self.MAKER_FEE, OkcoinApi.instance(), is_using_taker_fee)

    @staticmethod
    def get_market_currency(target_currency: str) -> "OkcoinCurrency":
        return OkcoinCurrency[target_currency.upper()]
