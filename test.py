from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency


def coinone_private_api_test():
    coinone_api = CoinoneApi()
    # print(coinone_api.get_balance())
    print(coinone_api.get_ticker(CoinoneCurrency.ETH))
    # print()


coinone_private_api_test()
