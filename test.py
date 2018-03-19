from api.coinone_api import CoinoneApi

coinapi = CoinoneApi()
coinapi.cancel_order("eth", 0, 0, 0)
