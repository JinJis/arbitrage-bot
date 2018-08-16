from api.okcoin_api import OkcoinApi
from api.currency import OkcoinCurrency
result = OkcoinApi.instance(is_public_access_only=False).order_limit_buy(OkcoinCurrency.BTC, 10000, 0.1)
print(result)
