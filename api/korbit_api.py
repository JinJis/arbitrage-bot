import requests
from .market_api import MarketApi
from .currency import KorbitCurrency
from bson import Decimal128
import configparser
from datetime import datetime


class KorbitApi(MarketApi):
    BASE_URL = "https://api.korbit.co.kr"

    def __init__(self, access_token_refresh_interval_in_minutes=30):
        self._expires_in_minutes = 60
        if access_token_refresh_interval_in_minutes >= self._expires_in_minutes:
            raise Exception("Korbit access token expires within 1 hour! Shorter refresh interval expected.")

        # in number of minutes
        self._access_token_refresh_interval_in_minutes = access_token_refresh_interval_in_minutes

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

        # in seconds
        expires_in = int(res_json["expires_in"])
        current_expires_in = self._expires_in_minutes * 60
        if expires_in is not current_expires_in:
            raise Exception("Seems like the expiration time for Korbit API access token has changed"
                            "(before: %d sec, after: %d sec)! Please verify." % (current_expires_in, expires_in))

        # save the current date for record
        self._access_token_last_updated = datetime.today()

    def refresh_access_token(self):
        res = requests.post(self.BASE_URL + "/v1/oauth2/access_token", data={
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token"
        })
        res_json = res.json()

        self._access_token = res_json["access_token"]
        self._refresh_token = res_json["refresh_token"]

        # save the current date for record
        self._access_token_last_updated = datetime.today()

    def get_access_token(self):
        # check if access token is within valid time
        # refresh access token if not
        delta = datetime.today() - self._access_token_last_updated
        if (delta.seconds / 60) >= self._access_token_refresh_interval_in_minutes:
            self.refresh_access_token()

        return self._access_token

    def get_balance(self):
        pass

    def order_buy(self, currency: KorbitCurrency, price: int, amount: float, order_type: str):
        pass

    def order_sell(self, currency: KorbitCurrency, price: int, amount: float, order_type: str):
        pass

    def cancel_order(self, currency: KorbitCurrency, price: int, amount: float, order_id: str, is_sell_order: bool):
        pass
