from trader.market_manager.bithumb_market_manager import BithumbMarketManager, BithumbCurrency
from trader.market_manager.coinone_market_manager import CoinoneMarketManager, CoinoneCurrency
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager, OkcoinCurrency
from trader.market_manager.gopax_market_manager import GopaxMarketManager, GopaxCurrency
from trader.market_manager.market_manager import MarketManager

bt_mm: MarketManager = BithumbMarketManager()
# co_mm: MarketManager = CoinoneMarketManager()
oc_mm: MarketManager = OkcoinMarketManager()
gp_mm: MarketManager = GopaxMarketManager()


order = gp_mm.order_buy(GopaxCurrency.XRP, 100, 10)
print(order.order_id)
print(order.order_type.value)
print(order.status)
print(order.order_amount)
print(order.currency)
gp_mm.cancel_order(GopaxCurrency.XRP, order)
