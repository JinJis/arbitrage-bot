from config.global_conf import Global
from .market_manager import MarketManager
from api.currency import GopaxCurrency
from api.gopax_api import GopaxApi
from trader.market.market import Market


class GopaxMarketManager(MarketManager):
    MARKET_TAG = Market.GOPAX
    TAKER_FEE = Global.read_market_fee(exchange_name="gopax", is_taker_fee=True)
    MAKER_FEE = Global.read_market_fee(exchange_name="gopax", is_taker_fee=False)

    def __init__(self, is_using_taker_fee: bool):
        super().__init__(self.MARKET_TAG, self.TAKER_FEE, self.MAKER_FEE, GopaxApi.instance(), is_using_taker_fee)

    @staticmethod
    def get_market_currency(target_currency: str) -> "GopaxCurrency":
        return GopaxCurrency[target_currency.upper()]
