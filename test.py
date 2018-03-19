# from api.coinone_api import CoinoneApi
#
# coinapi = CoinoneApi()
# coinapi.cancel_order("eth", 0, 0, 0)

from urllib import parse

abc = {
    "asdf": "dfdf",
    "sdfa": "asdf"
}

print(parse.urlencode(abc))
