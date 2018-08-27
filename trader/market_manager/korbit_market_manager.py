from config.global_conf import Global
from .market_manager import MarketManager
from api.currency import KorbitCurrency
from api.korbit_api import KorbitApi
from trader.market.market import Market


class KorbitMarketManager(MarketManager):
    MARKET_TAG = Market.KORBIT
    TAKER_FEE = Global.read_market_fee(exchange_name="korbit", is_taker_fee=True)
    MAKER_FEE = Global.read_market_fee(exchange_name="korbit", is_taker_fee=False)

    def __init__(self, is_using_taker_fee: bool):
        super().__init__(self.MARKET_TAG, self.TAKER_FEE, self.MAKER_FEE, KorbitApi.instance(), is_using_taker_fee)

    @staticmethod
    def get_market_currency(target_currency: str) -> "KorbitCurrency":
        return KorbitCurrency[target_currency.upper()]
