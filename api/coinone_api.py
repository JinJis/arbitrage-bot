import requests


class CoinoneApi:
    host_root = "https://api.coinone.co.kr"
    detailed_ticker_columns = ("timestamp", "result", "errorCode",
                               "high", "low", "last", "first", "volume",
                               "yesterday_high", "yesterday_low", "yesterday_last",
                               "yesterday_first", "yesterday_volume")
    orderbook_columns = ("timestamp", "result", "errorCode", "bid", "ask")
    list_of_filled_orders_columns = ("timestamp", "result", "errorCode", "completeOrders")
    lofo_complete_orders_columns = ("timestamp", "price", "qty")

    def __init__(self, currency):
        self.currency = {
            "eth_krw": "eth",
            "btc_krw": "btc"
        }.get(currency, "btc")

    def get_detailed_ticker(self):
        r = requests.get("%s/ticker?currency=%s" % (CoinoneApi.host_root, self.currency))
        if r.status_code == 200:
            data = r.json()
            return tuple(map(lambda x: data.get(x), CoinoneApi.detailed_ticker_columns))
        else:
            err = (r.status_code, "fail", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            return err

    def get_orderbook(self):
        r = requests.get("%s/orderbook?currency=%s" % (CoinoneApi.host_root, self.currency))
        if r.status_code == 200:
            data = r.json()
            return tuple(map(lambda x: data.get(x), CoinoneApi.orderbook_columns))
        else:
            err = (r.status_code, "fail", 0, "e", "e")
            return err

    # time_range can be hour, or day
    def get_list_of_filled_orders(self, time_range):
        r = requests.get("%s/trades?currency=%s&period=%s" % (CoinoneApi.host_root, self.currency, time_range))
        if r.status_code == 200:
            data = r.json()
            # it is an array, not a tuple
            return data.get(CoinoneApi.list_of_filled_orders_columns[3])
        else:
            print("Lofo from Coinone failed!", r.status_code)
            return []
