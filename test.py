from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency


def coinone_private_api_test():
    coinone_api = CoinoneApi()
    print(coinone_api.get_balance())


# coinone_private_api_test()

def cool(is_sell_order: bool):
    test = {
        "is_ask": 1 if is_sell_order else 0,
    }
    print(test)
#
#
# cool(CoinoneCurrency.ETH)
# print(CoinoneCurrency["eth".upper()].value)
cool(False)

