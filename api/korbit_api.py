import requests
from .market_api import MarketApi
from .currency import KorbitCurrency


class KorbitApi(MarketApi):
    BASE_URL = "https://api.korbit.co.kr/v1"

    def __init__(self):
        pass

    def get_ticker(self, currency: KorbitCurrency):
        pass

    def get_filled_orders(self, currency: KorbitCurrency):
        pass

    def get_detailed_ticker(self):
        r = requests.get("%s/ticker/detailed?currency_pair=%s" % (KorbitApi.host_root, self.currency))
        if r.status_code == 200:
            data = r.json()
            return tuple(map(lambda x: data.get(x), KorbitApi.detailed_ticker_columns))
        else:
            err = (r.status_code, 0, 0, 0, 0, 0, 0, 0, 0)
            return err

    def get_orderbook(self):
        r = requests.get("%s/orderbook?currency_pair=%s" % (KorbitApi.host_root, self.currency))
        if r.status_code == 200:
            data = r.json()
            return tuple(map(lambda x: data.get(x), KorbitApi.orderbook_columns))
        else:
            err = (r.status_code, "e", "e")
            return err

    # time_range can be minute, hour, or day
    def get_list_of_filled_orders(self, time_range):
        r = requests.get("%s/transactions?currency_pair=%s&time=%s" % (KorbitApi.host_root, self.currency, time_range))
        if r.status_code == 200:
            # it is an array, not a tuple
            return r.json()
        else:
            print("Lofo from Korbit failed!", r.status_code)
            return []
