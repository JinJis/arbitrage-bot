from api.gopax_api import GopaxApi
from api.currency import GopaxCurrency

gopax_api = GopaxApi.instance(is_public_access_only=True)
print(gopax_api.get_ticker(GopaxCurrency.BCH))
