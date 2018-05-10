import hmac
import json
import time
import base64
import hashlib
from operator import itemgetter
from requests import Response
import configparser
from bson import Decimal128
from datetime import datetime
from .market_api import MarketApi
from .currency import CoinoneCurrency
from config.global_conf import Global
from .coinone_error import CoinoneError
from trader.market.order import Order, OrderStatus

# in order to match the korbit orderbook item count
orderbook_item_limit = 30
# coinone access token expires in 30 days
access_token_refresh_interval_in_days = 1


class CoinoneApi(MarketApi):
    BASE_URL = "https://api.coinone.co.kr"

    def __init__(self, is_public_access_only=False):
        super().__init__(is_public_access_only)
        if not is_public_access_only:
            # in number of days
            self._access_token_refresh_interval_in_days = access_token_refresh_interval_in_days

            # set instance wide config
            self._config = configparser.ConfigParser()
            self._config.read(Global.USER_CONFIG_LOCATION)

            # set initial access_token & secret_key
            self._access_token = self._config["COINONE"]["access_token"]
            self._secret_key = self._config["COINONE"]["secret_key"]

            # refresh access token to make sure it has enough grace time than the set interval
            self._access_token_last_updated = None
            self.refresh_access_token()

    def get_ticker(self, currency: CoinoneCurrency):
        res = self._session.get(self.BASE_URL + "/ticker", params={
            "currency": currency.value
        })
        res_json = self.filter_successful_response(res)

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
        res = self._session.get(self.BASE_URL + "/orderbook", params={
            "currency": currency.value
        })
        res_json = self.filter_successful_response(res)

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
    def get_filled_orders(self, currency: CoinoneCurrency, time_range: str = "hour"):
        res = self._session.get(self.BASE_URL + "/trades", params={
            "currency": currency.value,
            "period": time_range
        })
        res_json = self.filter_successful_response(res)

        result = list()
        for _item in res_json["completeOrders"]:
            item = {
                "timestamp": int(_item["timestamp"]),
                "price": Decimal128(_item["price"]),
                "amount": Decimal128(_item["qty"])
            }
            result.append(item)

        # sort it before return cause coinone api does not return the orders in recent occurrence
        result.sort(key=itemgetter("timestamp"), reverse=True)

        return result

    def refresh_access_token(self):
        # request for refresh, save in config file
        res = self._session.post(self.BASE_URL + "/oauth/refresh_token", data={
            "access_token": self._access_token
        })
        res_json = self.filter_successful_response(res)

        # write in config file
        self._access_token = res_json["accessToken"]
        self._config["COINONE"]["access_token"] = self._access_token

        with open(Global.USER_CONFIG_LOCATION, "w") as config_file:
            self._config.write(config_file)

        # save the current date for record
        self._access_token_last_updated = datetime.today()

    def get_access_token(self):
        # check if access token is within valid time
        # refresh access token if not
        delta = datetime.today() - self._access_token_last_updated
        if delta.days >= self._access_token_refresh_interval_in_days:
            # make it thread safe
            with self.__access_token_lock:
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

        res = self._session.post(url, headers={
            "X-COINONE-PAYLOAD": encoded_payload,
            "X-COINONE-SIGNATURE": signature
        }, json=payload)
        res_json = self.filter_successful_response(res)

        return res_json

    def get_balance(self):
        res_json = self.coinone_post(self.BASE_URL + "/v2/account/balance")

        result = dict()
        for coin_name in res_json.keys():
            coin_balance = res_json[coin_name]
            if not isinstance(coin_balance, dict):
                continue
            _a = coin_balance.get("avail")
            _b = coin_balance.get("balance")

            # note that there's some attr we don't need in api response
            if _a is not None and _b is not None:
                available = float(_a)
                balance = float(_b)
                result[coin_name] = {
                    "available": available,
                    "trade_in_use": (balance - available),
                    "balance": balance
                }
        return result

    def order_limit_buy(self, currency: CoinoneCurrency, price: int, amount: float):
        # {"errorCode": "0","orderId": "8a82c561-40b4-4cb3-9bc0-9ac9ffc1d63b","result": "success"}
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

    def cancel_order(self, currency: CoinoneCurrency, order: Order):
        return self.coinone_post(self.BASE_URL + "/v2/order/cancel", payload={
            "order_id": order.order_id,
            "price": order.price,
            "qty": order.order_amount,
            "is_ask": 1 if order.is_sell_order() else 0,
            "currency": currency.value
        })

    def get_order_info(self, currency: CoinoneCurrency, order_id: str):
        res_json = self.coinone_post(self.BASE_URL + "/v2/order/order_info", payload={
            "order_id": order_id,
            "currency": currency.value
        })

        order_info = res_json["info"]
        order_amount = float(order_info["qty"])
        remain_amount = float(order_info["remainQty"])

        return {
            "status": OrderStatus.get(res_json["status"]),
            "avg_filled_price": int(float(order_info["price"])),
            "order_amount": order_amount,
            "filled_amount": order_amount - remain_amount,
            "remain_amount": remain_amount,
            "fee": float(order_info["fee"])
        }

    def get_open_orders(self, currency: CoinoneCurrency):
        return self.coinone_post(self.BASE_URL + "/v2/order/limit_orders", payload={
            "currency": currency.value
        })

    def get_past_trades(self, currency: CoinoneCurrency):
        return self.coinone_post(self.BASE_URL + "/v2/order/complete_orders", payload={
            "currency": currency.value
        })

    @staticmethod
    def filter_successful_response(res: Response):
        if res.status_code != 200:
            raise Exception("Network request has failed! (status code: %d)" % res.status_code)
        else:
            res_json = res.json()
            if res_json["result"] == "error":
                try:
                    raise CoinoneError(int(res_json["errorCode"]))
                except ValueError:
                    raise Exception("Unknown CoinoneError! %s" % res_json)
            elif res_json["result"] != "success":
                raise Exception("Unknown response: %s" % res_json)
            else:
                return res_json
