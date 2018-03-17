import requests
from .market_api import MarketApi
from .currency import CoinoneCurrency
from bson import Decimal128
import configparser
from datetime import date
import hmac
import json
import base64
import hashlib
import time

orderbook_item_limit = 30


class CoinoneApi(MarketApi):
    BASE_URL = "https://api.coinone.co.kr"

    def __init__(self, access_token_refresh_interval=5):
        # in number of days
        # make sure initial access token have more grace time than the given duration
        self._access_token_refresh_interval = access_token_refresh_interval
        self._access_token = None
        self._access_token_last_updated = None
        self._secret_key = None
        self.set_access_token()
        self.set_secret_key()

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

    def set_secret_key(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        self._secret_key = config["COINONE"]["SecretKey"]

    @staticmethod
    def encode_payload(payload):
        payload_json_bytes = json.dumps(payload).encode("utf-8")
        return base64.b64encode(payload_json_bytes)

    def get_signature(self, encoded_payload):
        secret_key_processed = str(self._secret_key).upper().encode("utf-8")
        return hmac.new(secret_key_processed, encoded_payload, hashlib.sha512).hexdigest()

    def coinone_post(self, url, payload=None):
        if payload is None:
            payload = dict()
        payload["access_token"] = self.get_access_token()
        payload["nonce"] = int(time.time())
        encoded_payload = self.encode_payload(payload)
        signature = self.get_signature(encoded_payload)

        res = requests.post(url, headers={
            "X-COINONE-PAYLOAD": encoded_payload,
            "X-COINONE-SIGNATURE": signature
        }, json=payload)

        return res.json()

    def get_balance(self):
        return self.coinone_post(self.BASE_URL + "/v2/account/balance")
