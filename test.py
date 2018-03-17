from api.coinone_api import CoinoneApi


def coinone_private_api_test():
    coinone_api = CoinoneApi()
    print(coinone_api.get_balance())


coinone_private_api_test()