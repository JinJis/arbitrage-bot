from api.bithumb_api import BithumbApi, BithumbCurrency
from api.coinone_api import CoinoneApi, CoinoneCurrency
from api.korbit_api import KorbitApi, KorbitCurrency
from api.gopax_api import GopaxApi, GopaxCurrency
from api.okcoin_api import OkcoinApi, OkcoinCurrency
from api.coinnest_api import CoinnestApi, CoinnestCurrency


# bt_api = BithumbApi.instance(is_public_access_only=False)
co_api = CoinoneApi.instance(is_public_access_only=False)
# kb_api = KorbitApi.instance()
# gp_api = GopaxApi.instance()
# oc_api = OkcoinApi.instance()
# cn_api = CoinnestApi.instance()


result = co_api.get_balance()
print(result)


