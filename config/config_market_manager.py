from enum import Enum
from trader.market_manager.bithumb_market_manager import BithumbMarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.gopax_market_manager import GopaxMarketManager
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager
from trader.market_manager.coinnest_market_manager import CoinnestMarketManager


class ConfigMarketManager(Enum):
    BITHUMB = BithumbMarketManager()
    COINONE = CoinoneMarketManager()
    # KORBIT = KorbitMarketManager()
    GOPAX = GopaxMarketManager()
    OKCOIN = OkcoinMarketManager()
    # COINNEST = CoinnestMarketManager()
