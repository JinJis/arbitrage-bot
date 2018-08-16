from config.global_conf import Global
from .market_manager import MarketManager
from api.currency import CoinoneCurrency
from api.coinone_api import CoinoneApi
from trader.market.market import Market


class CoinoneMarketManager(MarketManager):
    MARKET_TAG = Market.COINONE
    TAKER_FEE = Global.read_market_fee(exchange_name="coinone", is_taker_fee=True)
    MAKER_FEE = Global.read_market_fee(exchange_name="coinone", is_taker_fee=False)

    def __init__(self, is_using_taker_fee: bool):
        super().__init__(self.MARKET_TAG, self.TAKER_FEE, self.MAKER_FEE, CoinoneApi.instance(), is_using_taker_fee)

    @staticmethod
    def get_market_currency(target_currency: str) -> "CoinoneCurrency":
        return CoinoneCurrency[target_currency.upper()]
