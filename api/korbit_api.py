import requests
from .market_api import MarketApi
from .currency import KorbitCurrency
from bson import Decimal128
import configparser
from datetime import date


class KorbitApi(MarketApi):
    BASE_URL = "https://api.korbit.co.kr"

    def __init__(self, access_token_refresh_interval_in_minutes=30):
        if access_token_refresh_interval_in_minutes >= 60:
            raise Exception("Korbit access token expires within 1 hour!")

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

    def set_access_token(self, grant_type="password"):
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

        token_api_path = "/v1/oauth2/access_token"

        url_path = self.BASE_API_URL + token_api_path
        if grant_type == "password":
            data = {"client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "username": self.USER_NAME,
                    "password": self.PASSWORD,
                    "grant_type": grant_type}
        elif grant_type == "refresh_token":
            data = {"client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "refresh_token": self.refresh_token,
                    "grant_type": grant_type}
        else:
            raise Exception("Unexpected grant_type")

        res = requests.post(url_path, data=data)
        result = res.json()
        self.access_token = result["access_token"]
        self.token_type = result["token_type"]
        self.refresh_token = result["refresh_token"]
        self.expire = result["expires_in"]
        return self.expire, self.access_token, self.refresh_token

    def get_access_token(self):
        if self._access_token is None:
            raise Exception("Need to call set_access_token() first!")
        else:
            return self._access_token

    def get_balance(self):
        pass

    def order_buy(self, currency: KorbitCurrency, price: int, amount: float, order_type: str):
        pass

    def order_sell(self, currency: KorbitCurrency, price: int, amount: float, order_type: str):
        pass

    def cancel_order(self, currency: KorbitCurrency, price: int, amount: float, order_id: str, is_sell_order: bool):
        pass
