import requests
from .market_api import MarketApi
from .currency import KorbitCurrency
from bson import Decimal128


class KorbitApi(MarketApi):
    BASE_URL = "https://api.korbit.co.kr"

    def __init__(self):
        pass

    def get_ticker(self, currency: KorbitCurrency):
        res = requests.get(self.BASE_URL + "/v1/ticker/detailed", params={
            "currency_pair": currency
        })
        # raise ValueError if no valid json exists
        res_json = res.json()

        # reformat result
        result = {
            "timestamp": res_json["timestamp"],
            "high": Decimal128(res_json["high"]),
            "low": Decimal128(res_json["low"]),
            "last": Decimal128(res_json["last"]),
            "minAsk": Decimal128(res_json["ask"]),
            "maxBid": Decimal128(res_json["bid"]),
            "volume": Decimal128(res_json["volume"])
        }

        # change & changePercent are not specified in official API
        # just to make sure in order to avoid KeyError
        change = res_json.get("change")
        change_percent = res_json.get("changePercent")

        if change is not None:
            result["change"] = Decimal128(change)

        if change_percent is not None:
            result["changePercent"] = Decimal128(change_percent)

        return result

    def get_orderbook(self, currency: KorbitCurrency):
        res = requests.get(self.BASE_URL + "/v1/orderbook", params={
            "currency_pair": currency
        })
        res_json = res.json()

        # normalize asks
        _asks = res_json["asks"]
        asks = list()
        for _ask in _asks:
            ask = {
                "price": Decimal128(_ask[0]),
                "amount": Decimal128(_ask[1])
            }
            asks.append(ask)

        # normalize bids
        _bids = res_json["bids"]
        bids = list()
        for _bid in _bids:
            bid = {
                "price": Decimal128(_bid[0]),
                "amount": Decimal128(_bid[1])
            }
            bids.append(bid)

        # reformat result
        result = {
            "timestamp": res_json["timestamp"],
            "asks": asks,
            "bids": bids,
        }

        return result

    # time_range can be "minute", "hour" or "day"
    def get_filled_orders(self, currency: KorbitCurrency, time_range: str):
        res = requests.get(self.BASE_URL + "/v1/transactions", params={
            "currency_pair": currency,
            "time": time_range
        })
        res_json = res.json()

        result = list()
        for _item in res_json:
            item = {
                "timestamp": _item["timestamp"],
                "price": Decimal128(_item["price"]),
                "amount": Decimal128(_item["amount"])
            }
            result.append(item)

        return result
