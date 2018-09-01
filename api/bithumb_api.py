import math
import hmac
import time
import base64
import hashlib
import logging
import configparser
from bson import Decimal128
from requests import Response
from .market_api import MarketApi
from urllib.parse import urlencode
from config.global_conf import Global
from .currency import BithumbCurrency
from .bithumb_error import BithumbError
from trader.market.order import Order, OrderStatus


class BithumbApi(MarketApi):
    BASE_URL = "https://api.bithumb.com"

    def __init__(self, is_public_access_only=False):
        super().__init__(is_public_access_only)
        if not is_public_access_only:
            # set instance wide config
            self._config = configparser.ConfigParser()
            self._config.read(Global.USER_CONFIG_LOCATION)

            # set initial api_key & secret_key
            self._api_key = self._config["BITHUMB"]["api_key"]
            self._secret_key = self._config["BITHUMB"]["secret_key"]

    def get_ticker(self, currency: BithumbCurrency):
        res = self._session.get(self.BASE_URL + "/public/ticker/%s" % currency.value)
        res_json = self.filter_successful_response(res)

        # reformat result
        result = {
            "timestamp": int((res_json["data"]["date"])),
            "opening_price": Decimal128(str(res_json["data"]["opening_price"])),
            "closing_price": Decimal128(str(res_json["data"]["closing_price"])),
            "min_price": Decimal128(str(res_json["data"]["min_price"])),
            "max_price": Decimal128(str(res_json["data"]["max_price"])),
            "average_price": Decimal128(str(res_json["data"]["average_price"])),
            "units_traded": Decimal128(str(res_json["data"]["units_traded"])),
            "volume_1day": Decimal128(str(res_json["data"]["volume_1day"])),
            "volume_7day": Decimal128(str(res_json["data"]["volume_7day"])),
            "buy": Decimal128(str(res_json["data"]["buy_price"])),
            "sell": Decimal128(str(res_json["data"]["sell_price"])),
            "24H_fluctate": Decimal128(str(res_json["data"]["24H_fluctate"])),
            "24H_fluctate_rate": Decimal128(str(res_json["data"]["24H_fluctate_rate"])),
        }

        return result

    # Public API

    def get_orderbook(self, currency: BithumbCurrency):
        res = self._session.get(self.BASE_URL + "/public/orderbook/%s" % currency.value)
        res_json = self.filter_successful_response(res)

        # normalize asks
        _asks = res_json["data"]["asks"]
        asks = list()
        for _ask in _asks[:30]:
            ask = {
                "price": Decimal128(str(_ask["price"])),
                "amount": Decimal128(str(_ask["quantity"]))
            }
            asks.append(ask)

        # normalize bids
        _bids = res_json["data"]["bids"]
        bids = list()
        for _bid in _bids[:30]:
            bid = {
                "price": Decimal128(str(_bid["price"])),
                "amount": Decimal128(str(_bid["quantity"]))
            }
            bids.append(bid)

        # reformat result
        result = {
            "asks": asks,
            "bids": bids
        }

        return result

    def get_filled_orders(self, currency: BithumbCurrency, time_range: str):
        pass

    # Private API

    @staticmethod
    def usec_time():
        mt = "%f %d" % math.modf(time.time())
        mt_array = mt.split(" ")[:2]
        return mt_array[1] + mt_array[0][2:5]

    def bithumb_post(self, url_path: str, payload: dict = None):
        if not payload:
            payload = dict()
        payload["endpoint"] = url_path
        urlencoded_payload = urlencode(payload)

        nonce = self.usec_time()
        splinter = chr(0)
        combined_data = url_path + splinter + urlencoded_payload + splinter + nonce

        utf8_data = combined_data.encode("utf-8")
        utf8_secret_key = self._secret_key.encode("utf-8")

        hash_data = hmac.new(bytes(utf8_secret_key), utf8_data, hashlib.sha512)
        utf8_hex_output = hash_data.hexdigest().encode("utf-8")

        api_sign = base64.b64encode(utf8_hex_output)
        utf8_api_sign = api_sign.decode("utf-8")

        headers = {
            "Api-Key": self._api_key,
            "Api-Sign": utf8_api_sign,
            "Api-Nonce": nonce
        }

        res = self._session.post(
            self.BASE_URL + url_path,
            headers=headers,
            data=payload
        )
        res_json = self.filter_successful_response(res)

        return res_json

    def get_balance(self):
        # ini 파일에 있는 Bithumb거래 코인만 따올수 있음 (b/c 반환되는 데이터가 코인별로 정리 X)
        all_res_json = self.bithumb_post("/info/balance", payload={"currency": "ALL"})

        result = dict()
        for key in dict(all_res_json["data"]).keys():
            if "total_" in str(key):

                currency_name = str(key).replace("total_", "")
                result[currency_name] = {
                    "available": all_res_json["data"]["available_%s" % currency_name],
                    "trade_in_use": all_res_json["data"]["in_use_%s" % currency_name],
                    "balance": all_res_json["data"][key]
                }

                continue
        return result

    def order_limit_buy(self, currency: BithumbCurrency, price: int, amount: float):
        res_json = self.bithumb_post("/trade/place", payload={"order_currency": currency.value,
                                                              "Payment_currency": "krw",
                                                              "units": amount,
                                                              "price": price,
                                                              "type": "bid"})
        # {"status": "0000", "order_id": "1428646963419", "data": []}
        return {
            "orderId": str(res_json["order_id"])
        }

    def order_limit_sell(self, currency: BithumbCurrency, price: int, amount: float):
        res_json = self.bithumb_post("/trade/place", payload={"order_currency": currency.value,
                                                              "Payment_currency": "krw",
                                                              "units": amount,
                                                              "price": price,
                                                              "type": "ask"})
        # {"status": "0000", "order_id": "1428646963419", "data": []}
        return {
            "orderId": str(res_json["order_id"])
        }

    def cancel_order(self, currency: BithumbCurrency, order: Order):
        return self.bithumb_post("/trade/cancel", payload={
            "type": order.order_type,
            "order_id": order.order_id,
            "currency": currency.value})

    def get_order_info(self, currency: BithumbCurrency, order: Order):

        # unlike other exchanges api, Bithumb requires additional 'order_type' param when request
        if (order.order_type.value == "limit_sell") or (order.order_type.value == "market_sell"):
            order_type = "ask"
        elif (order.order_type.value == "limit_buy") or (order.order_type.value == "market_buy"):
            order_type = "bid"
        else:
            raise BithumbError("Unknow order_type doesn't exist %s" % order.order_type.value)

        # if no trade_info --> {'status': '5600', 'message': '거래 체결내역이 존재하지 않습니다.'}
        res_json = self.bithumb_post("/info/order_detail", payload={"order_id": order.order_id,
                                                                    "type": order_type,
                                                                    "currency": currency.value})

        order_data = res_json["data"][0]
        order_amount = float(order.order_amount)
        filled_amount = float(order_data["units_traded"])
        fee = order_data.get("fee")
        avg_filled_price = order_data["price"]

        return {
            "status": OrderStatus.get(res_json["status"]),
            "avg_filled_price": int(float(avg_filled_price)) if avg_filled_price is not None else "null",
            "order_amount": order_amount,
            "filled_amount": filled_amount,
            "remain_amount": order_amount - filled_amount,
            "fee": float(fee) if fee is not None else "null"
        }

    # there is no function..
    def get_open_orders(self, currency: BithumbCurrency):
        pass

    def get_past_trades(self, currency: BithumbCurrency, off_set: int = 0, limit: int = 50):
        return self.bithumb_post("/info/user_transactions", payload={"offset": off_set,
                                                                     "count": limit,
                                                                     "searchGb": 0,
                                                                     "currency": currency.value})

    def get_user_account_info(self, currency: BithumbCurrency):
        return self.bithumb_post("/info/account", payload={"currency": currency.value})

    def get_wallet_address(self, currency: BithumbCurrency):
        res_json = self.bithumb_post("/info/wallet_address", payload={"currency": currency.value})
        return res_json["data"]["wallet_address"]

    def get_krw_deposit_info(self):
        return self.bithumb_post("/trade/krw_deposit", payload=None)

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
                        raise BithumbError(error_msg)

            return res_json
