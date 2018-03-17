import requests
from .market_api import MarketApi
from .currency import CoinoneCurrency
from bson import Decimal128
import configparser
from datetime import date

orderbook_item_limit = 30


class CoinoneApi(MarketApi):
    BASE_URL = "https://api.coinone.co.kr"

    def __init__(self, access_token_refresh_interval=5):
        # in days, initial access token should have more grace time than this number
        self._access_token_refresh_interval = access_token_refresh_interval
        self._access_token = None
        self._access_token_last_updated = None
        self.set_access_token()

    def get_ticker(self, currency: CoinoneCurrency):
        res = requests.get(self.BASE_URL + "/ticker", params={
            "currency": currency
        })
        res_json = res.json()

        # reformat result
        result = {
            "timestamp": int(res_json["timestamp"]),
            "high": Decimal128(res_json["high"]),
            "low": Decimal128(res_json["low"]),
            "last": Decimal128(res_json["last"]),
            "first": Decimal128(res_json["first"]),
            "volume": Decimal128(res_json["volume"]),
            "yesterdayHigh": Decimal128(res_json["yesterday_high"]),
            "yesterdayLow": Decimal128(res_json["yesterday_low"]),
            "yesterdayLast": Decimal128(res_json["yesterday_last"]),
            "yesterdayFirst": Decimal128(res_json["yesterday_first"]),
            "yesterdayVolume": Decimal128(res_json["yesterday_volume"]),
        }

        return result

    def get_orderbook(self, currency: CoinoneCurrency):
        res = requests.get(self.BASE_URL + "/orderbook", params={
            "currency": currency
        })
        res_json = res.json()

        # normalize asks
        _asks = res_json["ask"]
        asks = list()
        for _ask in _asks[:orderbook_item_limit]:
            ask = {
                "price": Decimal128(_ask["price"]),
                "amount": Decimal128(_ask["qty"])
            }
            asks.append(ask)

        # normalize bids
        _bids = res_json["bid"]
        bids = list()
        for _bid in _bids[:orderbook_item_limit]:
            bid = {
                "price": Decimal128(_bid["price"]),
                "amount": Decimal128(_bid["qty"])
            }
            bids.append(bid)

        # reformat result
        result = {
            "timestamp": int(res_json["timestamp"]),
            "asks": asks,
            "bids": bids,
        }

        return result

    # time_range can be "hour" or "day"
    def get_filled_orders(self, currency: CoinoneCurrency, time_range: str):
        res = requests.get(self.BASE_URL + "/trades", params={
            "currency": currency,
            "period": time_range
        })
        res_json = res.json()

        result = list()
        for _item in res_json["completeOrders"]:
            item = {
                "timestamp": int(_item["timestamp"]),
                "price": Decimal128(_item["price"]),
                "amount": Decimal128(_item["qty"])
            }
            result.append(item)

        return result

    def set_access_token(self, should_refresh=False):
        config = configparser.ConfigParser()
        config.read("config.ini")
        # request for refresh if needed
        # then save in config file
        if should_refresh:
            res = requests.post(self.BASE_URL + "/oauth/refresh_token", headers={
                "content-type": "application/x-www-form-urlencoded"
            }, data={
                "access_token": self._access_token
            })
            res_json = res.json()
            self._access_token = res_json["accessToken"]
            config["COINONE"]["AccessToken"] = self._access_token
            with open("config.ini", "w") as config_file:
                config.write(config_file)
        # read directly from config file
        else:
            self._access_token = config["COINONE"]["AccessToken"]
        # save the current date for record
        self._access_token_last_updated = date.today()

    def get_access_token(self):
        delta = date.today() - self._access_token_last_updated
        if delta.days >= self._access_token_refresh_interval:
            self.set_access_token(should_refresh=True)
        return self._access_token
