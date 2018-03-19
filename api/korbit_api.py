import requests
from .market_api import MarketApi
from .currency import KorbitCurrency
from bson import Decimal128
import configparser
from datetime import datetime
import time
from urllib import parse


class KorbitApi(MarketApi):
    BASE_URL = "https://api.korbit.co.kr"

    def __init__(self):
        # set instance wide config
        self._config = configparser.ConfigParser()
        self._config.read("config.ini")

        # set initial access_token & secret_key
        self._client_id = self._config["KORBIT"]["ClientId"]
        self._client_secret = self._config["KORBIT"]["ClientSecret"]
        self._username = self._config["KORBIT"]["Username"]
        self._password = self._config["KORBIT"]["Password"]

        # set initial access token
        self._access_token = None
        # korbit has an extra token for refresh request
        self._refresh_token = None
        self._access_token_last_updated = None
        # korbit provides expiration time of access token
        self._expires_in_seconds = None
        self.set_access_token()

    def get_ticker(self, currency: KorbitCurrency):
        res = requests.get(self.BASE_URL + "/v1/ticker/detailed", params={
            "currency_pair": currency.value
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
            "currency_pair": currency.value
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
            "currency_pair": currency.value,
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

    def set_access_token(self):
        res = requests.post(self.BASE_URL + "/v1/oauth2/access_token", data={
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._username,
            "password": self._password,
            "grant_type": "password"
        })
        res_json = res.json()

        self._access_token = res_json["access_token"]
        self._refresh_token = res_json["refresh_token"]
        self._expires_in_seconds = int(res_json["expires_in"])

        # save the current date for record
        self._access_token_last_updated = datetime.today()

    def refresh_access_token(self):
        res = requests.post(self.BASE_URL + "/v1/oauth2/access_token", data={
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token"
        })
        res_json = res.json()

        self._access_token = res_json["access_token"]
        self._refresh_token = res_json["refresh_token"]
        self._expires_in_seconds = int(res_json["expires_in"])

        # save the current date for record
        self._access_token_last_updated = datetime.today()

    def get_access_token(self):
        # check if access token is within valid time
        delta = datetime.today() - self._access_token_last_updated
        # korbit expires the access token within an hour
        # the api gives specific number on the expiration time
        # here we are refreshing the access token 5 minutes before it expires
        if delta.seconds >= (self._expires_in_seconds - 60 * 5):
            self.refresh_access_token()

        return self._access_token

    def get_auth_header(self):
        return {
            "Authorization": "Bearer " + self._access_token
        }

    @staticmethod
    def get_nonce():
        return int(time.time())

    def get_balance(self):
        res = requests.get(self.BASE_URL + "/v1/user/balances", headers=self.get_auth_header())
        return res.json()

    def order_limit_buy(self, currency: KorbitCurrency, price: int, amount: float):
        res = requests.post(self.BASE_URL + "/v1/user/orders/buy", headers=self.get_auth_header(), data={
            "currency_pair": currency.value,
            "type": "limit",
            "price": price,
            "coin_amount": amount,
            "nonce": self.get_nonce()
        })
        return res.json()

    def order_limit_sell(self, currency: KorbitCurrency, price: int, amount: float):
        res = requests.post(self.BASE_URL + "/v1/user/orders/sell", headers=self.get_auth_header(), data={
            "currency_pair": currency.value,
            "type": "limit",
            "price": price,
            "coin_amount": amount,
            "nonce": self.get_nonce()
        })
        return res.json()

    def order_market_buy(self, currency: KorbitCurrency, amount_of_krw: int):
        res = requests.post(self.BASE_URL + "/v1/user/orders/buy", headers=self.get_auth_header(), data={
            "currency_pair": currency.value,
            "type": "market",
            "fiat_amount": amount_of_krw,
            "nonce": self.get_nonce()
        })
        return res.json()

    def order_market_sell(self, currency: KorbitCurrency, amount_of_coin: float):
        res = requests.post(self.BASE_URL + "/v1/user/orders/sell", headers=self.get_auth_header(), data={
            "currency_pair": currency.value,
            "type": "market",
            "coin_amount": amount_of_coin,
            "nonce": self.get_nonce()
        })
        return res.json()

    def cancel_order(self, currency: KorbitCurrency, order_ids: list):
        data = {
            "currency_pair": currency.value,
            "nonce": self.get_nonce()
        }
        encoded_data = parse.urlencode(data)

        # korbit supports cancelling multiple orders
        # append all order ids to encoded data
        for order_id in order_ids:
            encoded_data += "&id=%s" % str(order_id)

        res = requests.post(self.BASE_URL + "/v1/user/orders/cancel", headers=self.get_auth_header(), data=encoded_data)
        return res.json()

    def get_order_info(self, currency: KorbitCurrency, order_id: str):
        res = requests.get(self.BASE_URL + "/v1/user/orders", headers=self.get_auth_header(), data={
            "currency_pair": currency.value,
            "id": order_id,
            "nonce": self.get_nonce()
        })
        return res.json()

    def get_open_orders(self, currency: KorbitCurrency, offset: int = 0, limit: int = 100):
        res = requests.get(self.BASE_URL + "/v1/user/orders/open", headers=self.get_auth_header(), data={
            "currency_pair": currency.value,
            "offset": offset,
            "limit": limit,
            "nonce": self.get_nonce()
        })
        return res.json()

    def get_past_trades(self, currency: KorbitCurrency, offset: int = 0, limit: int = 100):
        res = requests.get(self.BASE_URL + "/v1/user/orders", headers=self.get_auth_header(), data={
            "currency_pair": currency.value,
            "offset": offset,
            "limit": limit,
            "nonce": self.get_nonce()
        })
        return res.json()
