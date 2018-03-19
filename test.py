from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency


def coinone_private_api_test():
    coinone_api = CoinoneApi()
    # print(coinone_api.get_balance())
    print(coinone_api.get_ticker(CoinoneCurrency.ETH))
    # print()


# coinone_private_api_test()

from datetime import datetime

a = datetime(2018, 3, 14, 12, 0, 0)
b = datetime.today()

print(a)
print(b)
print((b-a).days)
