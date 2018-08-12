import configparser
from bson import Decimal128
from requests import Response
from config.global_conf import Global
from trader.market.order import Order
from .currency import BithumbCurrency
from .market_api import MarketApi
from trader.market.order import OrderStatus
from .bithumb_error import BithumbError
import logging
import hashlib
import base64
import json
import time
import hmac


class BithumbApi(MarketApi):
    BASE_URL = "https://api.bithumb.com"

    def __init__(self, is_public_access_only=False):
        super().__init__(is_public_access_only)
        if not is_public_access_only:
            # set instance wide config
            self._config = configparser.ConfigParser()
            self._config.read(Global.USER_CONFIG_LOCATION)

            # set initial api_key & secret_key
            self._connect_key = self._config["BITHUMB"]["connect_key"]
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

    def get_balance(self):
        pass

    def order_limit_buy(self, currency: BithumbCurrency, price: int, amount: float):
        pass

    def order_limit_sell(self, currency: BithumbCurrency, price: int, amount: float):
        pass

    def cancel_order(self, currency: BithumbCurrency, order: Order):
        pass

    def get_order_info(self, currency: BithumbCurrency, order_id: str):
        pass

    def get_open_orders(self, currency: BithumbCurrency):
        pass

    def get_past_trades(self, currency: BithumbCurrency):
        pass

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
