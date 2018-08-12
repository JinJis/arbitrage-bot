from api.bithumb_api import BithumbApi, BithumbCurrency
from api.coinone_api import CoinoneApi, CoinoneCurrency
from api.korbit_api import KorbitApi, KorbitCurrency
from api.gopax_api import GopaxApi, GopaxCurrency
from api.okcoin_api import OkcoinApi, OkcoinCurrency
from api.coinnest_api import CoinnestApi, CoinnestCurrency


bt_api = BithumbApi.instance()
co_api = CoinoneApi.instance()
kb_api = KorbitApi.instance()
gp_api = GopaxApi.instance()
oc_api = OkcoinApi.instance()
cn_api = CoinnestApi.instance()


print(bt_api.get_orderbook(BithumbCurrency.TRON))
print(co_api.get_orderbook(CoinoneCurrency.TRON))
print(oc_api.get_orderbook(OkcoinCurrency.TRON))
print(cn_api.get_orderbook(CoinnestCurrency.TRON))

