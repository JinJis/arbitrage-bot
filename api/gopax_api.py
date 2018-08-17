import configparser
from bson import Decimal128
from requests import Response
from config.global_conf import Global
from trader.market.order import Order
from .currency import GopaxCurrency
from .market_api import MarketApi
from trader.market.order import OrderStatus
from .gopax_error import GopaxError
import logging
import hashlib
import base64
import json
import time
import hmac


class GopaxApi(MarketApi):
    BASE_URL = "https://api.gopax.co.kr"

    def __init__(self, is_public_access_only=False):
        super().__init__(is_public_access_only)
        if not is_public_access_only:
            # set instance wide config
            self._config = configparser.ConfigParser()
            self._config.read(Global.USER_CONFIG_LOCATION)

            # set initial api_key & secret_key
            self._access_token = self._config["GOPAX"]["access_token"]
            self._secret_key = self._config["GOPAX"]["secret_key"]

    # Public API

    def get_ticker(self, currency: GopaxCurrency):
        res = self._session.get(self.BASE_URL + "/trading-pairs/%s/stats" % currency.value)
        res_json = self.filter_successful_response(res)

        # reformat result
        result = {
            "timestamp": Global.iso8601_to_unix(res_json["time"]),
            "open": Decimal128(str(res_json["open"])),
            "close": Decimal128(str(res_json["close"])),
            "high": Decimal128(str(res_json["high"])),
            "low": Decimal128(str(res_json["low"])),
            "volume": Decimal128(str(res_json["volume"]))
        }

        return result

    def get_orderbook(self, currency: GopaxCurrency):
        res = self._session.get(self.BASE_URL + "/trading-pairs/%s/book" % currency.value)
        res_json = self.filter_successful_response(res)

        # normalize asks
        _asks = res_json["ask"]
        asks = list()
        for _ask in _asks[:30]:
            ask = {
                "price": Decimal128(str(_ask[1])),
                "amount": Decimal128(str(_ask[2]))
            }
            asks.append(ask)

        # normalize bids
        _bids = res_json["bid"]
        bids = list()
        for _bid in _bids[:30]:
            bid = {
                "price": Decimal128(str(_bid[1])),
                "amount": Decimal128(str(_bid[2]))
            }
            bids.append(bid)

        # reformat result
        result = {
            "asks": asks,
            "bids": bids
        }

        return result

    def get_filled_orders(self, currency: GopaxCurrency, time_range: str):
        super().get_filled_orders(currency, time_range)

    # Private API

    def get_auth_headers(self, http_method: str, request_path: str, json_body: str = None):
        nonce = str(time.time())
        what = nonce + http_method + request_path
        if json_body:
            what += json_body
        key = base64.b64decode(self._secret_key)
        signature = hmac.new(key, str(what).encode("utf-8"), hashlib.sha512)
        signature_b64 = base64.b64encode(signature.digest())

        return {
            "API-Key": self._access_token,
            "Signature": signature_b64,
            "Nonce": nonce
        }

    def get_balance(self):
        path = "/balances"
        headers = self.get_auth_headers("GET", path)
        res = self._session.get(self.BASE_URL + path, headers=headers)
        res_json = self.filter_successful_response(res)

        result = dict()
        for asset_item in res_json:
            coin_name = str(asset_item["asset"]).lower()
            available = float(asset_item["avail"])
            trade_in_use = float(asset_item["hold"])
            result[coin_name] = {
                "available": available,
                "trade_in_use": trade_in_use,
                "balance": available + trade_in_use
            }
        return result

    def order_limit_buy(self, currency: GopaxCurrency, price: int, amount: float):
        path = "/orders"
        body = {
            "type": "limit",
            "side": "buy",
            "price": price,
            "amount": amount,
            "tradingPairName": currency.value
        }
        json_body = json.dumps(body, sort_keys=True)
        headers = self.get_auth_headers("POST", path, json_body)
        res = self._session.post(self.BASE_URL + path, headers=headers, data=json_body)
        res_json = self.filter_successful_response(res)
        return {
            "orderId": str(res_json["id"])
        }

    def order_limit_sell(self, currency: GopaxCurrency, price: int, amount: float):
        path = "/orders"
        body = {
            "type": "limit",
            "side": "sell",
            "price": price,
            "amount": amount,
            "tradingPairName": currency.value
        }
        json_body = json.dumps(body, sort_keys=True)
        headers = self.get_auth_headers("POST", path, json_body)
        res = self._session.post(self.BASE_URL + path, headers=headers, data=json_body)
        res_json = self.filter_successful_response(res)
        return {
            "orderId": str(res_json["id"])
        }

    def cancel_order(self, currency: GopaxCurrency, order: Order):
        path = "/orders/" + order.order_id
        headers = self.get_auth_headers("DELETE", path)
        res = self._session.delete(self.BASE_URL + path, headers=headers)
        res_json = self.filter_successful_response(res)
        return res_json

    def get_order_info(self, currency: GopaxCurrency, order: Order):
        path = "/orders/" + order.order_id
        headers = self.get_auth_headers("GET", path)
        res = self._session.get(self.BASE_URL + path, headers=headers)
        res_json = self.filter_successful_response(res)

        # note that if res_json is empty it will return empty
        # gopax api is currently removing the order entry when the order is completed or cancelled, which is very wrong.
        if res_json is None:
            return None

        fee_rate = Global.read_market_fee("gopax", is_taker_fee=True)

        order_amount = float(res_json["amount"])
        remain_amount = float(res_json["remaining"])
        filled_amount = order_amount - remain_amount
        avg_filled_price = int(float(res_json["price"]))

        if res_json["side"] == "buy":
            fee = filled_amount * fee_rate
        elif res_json["side"] == "sell":
            fee = avg_filled_price * filled_amount * fee_rate
        else:
            fee = 0

        return {
            "status": OrderStatus.get(res_json["status"]),
            "avg_filled_price": avg_filled_price,
            "order_amount": order_amount,
            "filled_amount": filled_amount,
            "remain_amount": remain_amount,
            "fee": fee
        }

    def get_open_orders(self, currency: GopaxCurrency):
        path = "/orders"
        headers = self.get_auth_headers("GET", path)
        res = self._session.get(self.BASE_URL + path, headers=headers, params={
            "trading-pair-name": currency.value
        })
        res_json = self.filter_successful_response(res)
        return res_json

    def get_past_trades(self, currency: GopaxCurrency):
        # maximum past 2 days order history will be shown
        path = "/trades"
        headers = self.get_auth_headers("GET", path)
        res = self._session.get(self.BASE_URL + path, headers=headers, params={
            "trading-pair-name": currency.value
        })
        res_json = self.filter_successful_response(res)
        return res_json

    @staticmethod
    def filter_successful_response(res: Response):
        if res.status_code != 200:
            raise Exception("Network request has failed! (status code: %d)" % res.status_code)
        else:
            res_json = res.json()

            if type(res_json) is dict:
                error_msg = res_json.get("errormsg")
                error_msg2 = res_json.get("errorMessage")
                error_code = res_json.get("errorCode")

                if error_msg or error_msg2 or error_code:
                    # no such order id error => but it happens even when the order is completed or cancelled
                    if error_code == 10069:
                        logging.debug(error_msg)
                        return None
                    else:
                        raise GopaxError(error_msg)

            return res_json
