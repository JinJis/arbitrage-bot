import requests
from .market_api import MarketApi
from .currency import CoinoneCurrency
from bson import Decimal128
import configparser
from datetime import datetime
import hmac
import json
import base64
import hashlib
import time

# in order to match the korbit orderbook item count
orderbook_item_limit = 30
# coinone access token expires in 30 days
access_token_refresh_interval_in_days = 1


class CoinoneApi(MarketApi):
    BASE_URL = "https://api.coinone.co.kr"

    def __init__(self):
        # in number of days
        self._access_token_refresh_interval_in_days = access_token_refresh_interval_in_days

        # set instance wide config
        self._config = configparser.ConfigParser()
        self._config.read("config/conf_user.ini")

        # set initial access_token & secret_key
        self._access_token = self._config["COINONE"]["AccessToken"]
        self._secret_key = self._config["COINONE"]["SecretKey"]

        # refresh access token to make sure it has enough grace time than the set interval
        self._access_token_last_updated = None
        self.refresh_access_token()

    def get_ticker(self, currency: CoinoneCurrency):
        res = requests.get(self.BASE_URL + "/ticker", params={
            "currency": currency.value
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
            "currency": currency.value
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
            "currency": currency.value,
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

    def refresh_access_token(self):
        # request for refresh, save in config file
        res = requests.post(self.BASE_URL + "/oauth/refresh_token", data={
            "access_token": self._access_token
        })
        res_json = res.json()

        # write in config file
        self._access_token = res_json["accessToken"]
        self._config["COINONE"]["AccessToken"] = self._access_token

        with open("config.ini", "w") as config_file:
            self._config.write(config_file)

        # save the current date for record
        self._access_token_last_updated = datetime.today()

    def get_access_token(self):
        # check if access token is within valid time
        # refresh access token if not
        delta = datetime.today() - self._access_token_last_updated
        if delta.days >= self._access_token_refresh_interval_in_days:
            self.refresh_access_token()

        return self._access_token

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

    def order_limit_buy(self, currency: CoinoneCurrency, price: int, amount: float):
        return self.coinone_post(self.BASE_URL + "/v2/order/limit_buy", payload={
            "price": price,
            "qty": amount,
            "currency": currency.value,
        })

    def order_limit_sell(self, currency: CoinoneCurrency, price: int, amount: float):
        return self.coinone_post(self.BASE_URL + "/v2/order/limit_sell", payload={
            "price": price,
            "qty": amount,
            "currency": currency.value,
        })

    def cancel_order(self, currency: CoinoneCurrency, price: int, amount: float, order_id: str, is_sell_order: bool):
        return self.coinone_post(self.BASE_URL + "/v2/order/cancel", payload={
            "order_id": order_id,
            "price": price,
            "qty": amount,
            "is_ask": 1 if is_sell_order else 0,
            "currency": currency.value
        })

    def get_order_info(self, currency: CoinoneCurrency, order_id: str):
        return self.coinone_post(self.BASE_URL + "/v2/order/order_info", payload={
            "order_id": order_id,
            "currency": currency.value
        })

    def get_open_orders(self, currency: CoinoneCurrency):
        return self.coinone_post(self.BASE_URL + "/v2/order/limit_orders", payload={
            "currency": currency.value
        })

    def get_past_trades(self, currency: CoinoneCurrency):
        return self.coinone_post(self.BASE_URL + "/v2/order/complete_orders", payload={
            "currency": currency.value
        })
