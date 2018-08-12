import configparser
from bson import Decimal128
from requests import Response
from config.global_conf import Global
from trader.market.order import Order
from .currency import OkcoinCurrency
from .market_api import MarketApi
from trader.market.order import OrderStatus
from .okcoin_error import OkcoinError
import logging
import hashlib
import base64
import json
import time
import hmac


class OkcoinApi(MarketApi):
    BASE_URL = "https://www.okcoinkr.com/api/v1"

    def __init__(self, is_public_access_only=False):
        super().__init__(is_public_access_only)
        if not is_public_access_only:
            # set instance wide config
            self._config = configparser.ConfigParser()
            self._config.read(Global.USER_CONFIG_LOCATION)

            # set initial api_key & secret_key
            self._api_key = self._config["OKCOIN"]["api_key"]
            self._secret_key = self._config["OKCOIN"]["secret_key"]

    def get_ticker(self, currency: OkcoinCurrency):
        res = self._session.get(self.BASE_URL + "/ticker.do?symbol=%s" % currency.value)
        res_json = self.filter_successful_response(res)

        # reformat result
        result = {
            "timestamp": int((res_json["date"])),
            "buy": Decimal128(str(res_json["ticker"]["buy"])),
            "sell": Decimal128(str(res_json["ticker"]["sell"])),
            "last": Decimal128(str(res_json["ticker"]["last"])),
            "high": Decimal128(str(res_json["ticker"]["high"])),
            "low": Decimal128(str(res_json["ticker"]["low"])),
            "volume": Decimal128(str(res_json["ticker"]["vol"]))
        }

        return result

    def get_orderbook(self, currency: OkcoinCurrency):
        res = self._session.get(self.BASE_URL + "/depth.do?symbol=%s" % currency.value)
        res_json = self.filter_successful_response(res)

        # normalize asks
        _asks = res_json["asks"]
        asks = list()
        for _ask in _asks[:30]:
            ask = {
                "price": Decimal128(str(_ask[0])),
                "amount": Decimal128(str(_ask[1]))
            }
            asks.append(ask)

        # normalize bids
        _bids = res_json["bids"]
        bids = list()
        for _bid in _bids[:30]:
            bid = {
                "price": Decimal128(str(_bid[0])),
                "amount": Decimal128(str(_bid[1]))
            }
            bids.append(bid)

        # reformat result
        result = {
            "asks": asks,
            "bids": bids
        }

        return result

    def get_filled_orders(self, currency: OkcoinCurrency, time_range: str):
        super().get_filled_orders(currency, time_range)

    def get_md5_sign(self, param_list: list):
        param_list.append("api_key=%s" % self._api_key)
        alphabetical_order_list = sorted(param_list)

        prev = None
        for ordered in alphabetical_order_list:
            if prev is None:
                prev = ordered
                continue
            else:
                prev += ("&" + ordered)

        reoredered = prev + str("&secret_key=%s" % self._secret_key)

        m = hashlib.md5()
        m.update(reoredered.encode('utf-8'))
        return m.hexdigest().upper()

    def get_balance(self):
        sign = self.get_md5_sign(param_list=[])
        res = self._session.get(self.BASE_URL + "/userinfo.do?api_key=%s?sign=%s" % (self._api_key, sign))
        res_json = self.filter_successful_response(res)
        print(res_json)

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

    def order_limit_buy(self, currency: OkcoinCurrency, price: int, amount: float):
        pass

    def order_limit_sell(self, currency: OkcoinCurrency, price: int, amount: float):
        pass

    def cancel_order(self, currency: OkcoinCurrency, order: Order):
        pass

    def get_order_info(self, currency: OkcoinCurrency, order_id: str):
        pass

    def get_open_orders(self, currency: OkcoinCurrency):
        pass

    def get_past_trades(self, currency: OkcoinCurrency):
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
                        raise GopaxError(error_msg)

            return res_json
