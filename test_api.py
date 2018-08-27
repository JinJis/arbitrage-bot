from api.bithumb_api import BithumbApi, BithumbCurrency
from api.coinone_api import CoinoneApi, CoinoneCurrency
from api.korbit_api import KorbitApi, KorbitCurrency
from api.gopax_api import GopaxApi, GopaxCurrency
from api.okcoin_api import OkcoinApi, OkcoinCurrency
from api.coinnest_api import CoinnestApi, CoinnestCurrency
from trader.market.order import Order, OrderType
from trader.market.market import Market

# bt_api = BithumbApi.instance(is_public_access_only=False)
co_api = CoinoneApi.instance(is_public_access_only=False)
# kb_api = KorbitApi.instance()
# gp_api = GopaxApi.instance()
# oc_api = OkcoinApi.instance(is_public_access_only=False)
# cn_api = CoinnestApi.instance()

# order = Order(Market.COINONE, CoinoneCurrency.TRON, OrderType.LIMIT_BUY, "70862443", 344300, 0.01)
result = co_api.get_orderbook(CoinoneCurrency.TRON)
# result = bt_api.order_limit_buy(BithumbCurrency.ETH, 343000, 0.01)
print(result)
