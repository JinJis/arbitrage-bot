import configparser
from bson import Decimal128
from requests import Response
from config.global_conf import Global
from trader.market.order import Order
from .currency import OkcoinCurrency
from .market_api import MarketApi
from trader.market.order import OrderStatus
from .okcoin_error import OkcoinError
import hashlib


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

    # Public API

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

        # min ask positioned at the last... exceptional case only for Okcoin
        reversed_asks = list(reversed(_asks))
        for _ask in reversed_asks[:30]:
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

    # Private API

    def okcoin_post(self, url, data: dict):
        res = self._session.post(url=url, data=data)
        return self.filter_successful_response(res)

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
        res_json = self.okcoin_post(self.BASE_URL + "/userinfo.do", data={
            "api_key": self._api_key,
            "sign": sign
        })

        result = dict()
        my_balance = res_json["info"]["funds"]
        for asset_item in my_balance["free"].keys():
            coin_name = str(asset_item).lower()
            available = float(my_balance["free"][coin_name])
            trade_in_use = float(my_balance["freezed"][coin_name])
            result[coin_name] = {
                "available": available,
                "trade_in_use": trade_in_use,
                "balance": available + trade_in_use
            }
        return result

    def order_limit_buy(self, currency: OkcoinCurrency, price: int, amount: float):
        # {"result":true,"order_id":123456}
        sign = self.get_md5_sign(param_list=["symbol=%s" % currency.value,
                                             "type=buy",
                                             "price=%s" % price,
                                             "amount=%s" % str(amount)])

        res_json = self.okcoin_post(self.BASE_URL + "/trade.do", data={"api_key": self._api_key,
                                                                       "symbol": currency.value,
                                                                       "type": "buy",
                                                                       "price": price,
                                                                       "amount": str(amount),
                                                                       "sign": sign})
        return {
            "orderId": res_json["order_id"]
        }

    def order_limit_sell(self, currency: OkcoinCurrency, price: int, amount: float):
        # {"result":true,"order_id":123456}
        sign = self.get_md5_sign(param_list=["symbol=%s" % currency.value,
                                             "type=sell",
                                             "price=%s" % price,
                                             "amount=%s" % str(amount)])

        res_json = self.okcoin_post(self.BASE_URL + "/trade.do", data={"api_key": self._api_key,
                                                                       "symbol": currency.value,
                                                                       "type": "sell",
                                                                       "price": price,
                                                                       "amount": str(amount),
                                                                       "sign": sign})
        return {
            "orderId": res_json["order_id"]
        }

    def cancel_order(self, currency: OkcoinCurrency, order: Order):
        # {"result":true,"order_id":123456}
        sign = self.get_md5_sign(param_list=["symbol=%s" % currency.value,
                                             "order_id=%s" % order.order_id])

        return self.okcoin_post(self.BASE_URL + "/cancel_order.do", data={"api_key": self._api_key,
                                                                          "symbol": currency.value,
                                                                          "order_id": order.order_id,
                                                                          "sign": sign})

    def get_order_info(self, currency: OkcoinCurrency, order: Order):
        sign = self.get_md5_sign(param_list=["symbol=%s" % currency.value,
                                             "order_id=%s" % order.order_id])

        res_json = self.okcoin_post(self.BASE_URL + "/order_info.do", data={"api_key": self._api_key,
                                                                            "symbol": currency.value,
                                                                            "order_id": order.order_id,
                                                                            "sign": sign})

        fee_rate = Global.read_market_fee("okcoin", is_taker_fee=True)

        order_info = res_json["orders"][0]
        order_amount = float(order_info["amount"])
        filled_amount = float(order_info["deal_amount"])
        avg_filled_price = int(float(order_info["avg_price"]))

        if order_info["type"] == "buy":
            fee = filled_amount * fee_rate
        elif order_info["type"] == "sell":
            fee = avg_filled_price * filled_amount * fee_rate
        else:
            fee = "null"

        # status: -1 = 취소 됨, 0 = 미체결, 1 = 부분 체결, 2 = 전부 체결, 3 = 주문취소 처리중
        return {
            "status": OrderStatus.get(order_info["status"]),
            "avg_filled_price": avg_filled_price,
            "order_amount": order_amount,
            "filled_amount": filled_amount,
            "remain_amount": order_amount - filled_amount,
            # fee 제공안함.. RFAB용이므로 Taker Fee로 계산함
            "fee": fee
        }

    def get_open_orders(self, currency: OkcoinCurrency, page: int = 1, limit: int = 100):
        # unfilled_order: status=0
        status = 0
        sign = self.get_md5_sign(param_list=["symbol=%s" % currency.value,
                                             "status=%d" % status,
                                             "current_page=%d" % page,
                                             "page_length=%d" % limit])

        return self.okcoin_post(self.BASE_URL + "/order_history.do", data={"api_key": self._api_key,
                                                                           "symbol": currency.value,
                                                                           "status": status,
                                                                           "current_page": page,
                                                                           "page_length": limit,
                                                                           "sign": sign})

    def get_past_trades(self, currency: OkcoinCurrency, page: int = 1, limit: int = 100):

        # filled order: status=2 / partially_filled: status=1
        status = 2
        sign = self.get_md5_sign(param_list=["symbol=%s" % currency.value,
                                             "status=%d" % status,
                                             "current_page=%d" % page,
                                             "page_length=%d" % limit])

        return self.okcoin_post(self.BASE_URL + "/order_history.do", data={"api_key": self._api_key,
                                                                           "symbol": currency.value,
                                                                           "status": status,
                                                                           "current_page": page,
                                                                           "page_length": limit,
                                                                           "sign": sign})

    def get_user_account_info(self):
        sign = self.get_md5_sign(param_list=[])
        res_json = self.okcoin_post(self.BASE_URL + "/userinfo.do", data={"api_key": self._api_key,
                                                                          "sign": sign})
        return res_json

    @staticmethod
    def filter_successful_response(res: Response):
        if res.status_code != 200:
            raise Exception("Network request has failed! (status code: %d)" % res.status_code)
        else:
            res_json = res.json()

            if type(res_json) is dict:
                error_code = res_json.get("code")
                error_msg = res_json.get("msg")

                if error_code or error_msg:
                    raise OkcoinError(error_code, error_msg)

            return res_json
