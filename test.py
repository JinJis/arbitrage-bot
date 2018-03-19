from api.korbit_api import KorbitApi
from api.currency import KorbitCurrency, CoinoneCurrency
from api.coinone_api import CoinoneApi

korbit_api = KorbitApi()
print(korbit_api.get_open_orders(KorbitCurrency.ETH))
print(korbit_api.get_balance())

# coinone_api = CoinoneApi()
# print(coinone_api.get_past_trades(CoinoneCurrency.ETH))
# print(coinone_api.get_open_orders(CoinoneCurrency.ETH))
