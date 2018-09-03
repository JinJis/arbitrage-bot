import configparser
import logging
from bson import Decimal128
from requests import Response
from config.global_conf import Global
from trader.market.order import Order
from .coinnest_error import CoinnestError
from .currency import CoinnestCurrency
from .market_api import MarketApi


class CoinnestApi(MarketApi):
    BASE_URL = "https://api.coinnest.co.kr"

    def __init__(self, is_public_access_only=False):
        super().__init__(is_public_access_only)
        if not is_public_access_only:
            # set instance wide config
            self._config = configparser.ConfigParser()
            self._config.read(Global.USER_CONFIG_LOCATION)

            # set initial api_key & secret_key
            self._public_key = self._config["COINNEST"]["public_key"]
            self._secret_key = self._config["COINNEST"]["secret_key"]

    def get_ticker(self, currency: CoinnestCurrency):
        res = self._session.get(self.BASE_URL + "/api/pub/ticker?coin=%s" % currency.value)
        res_json = self.filter_successful_response(res)

        # reformat result
        result = {
            "timestamp": int((res_json["time"])),
            "buy": Decimal128(str(res_json["buy"])),
            "sell": Decimal128(str(res_json["sell"])),
            "last": Decimal128(str(res_json["last"])),
            "high": Decimal128(str(res_json["high"])),
            "low": Decimal128(str(res_json["low"])),
            "volume": Decimal128(str(res_json["vol"]))
        }

        return result

    def get_orderbook(self, currency: CoinnestCurrency):
        res = self._session.get(self.BASE_URL + "/api/pub/depth?coin=%s" % currency.value)
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

    def get_filled_orders(self, currency: CoinnestCurrency, time_range: str):
        pass

    def get_balance(self):
        pass

    def order_limit_buy(self, currency: CoinnestCurrency, price: int, amount: float):
        pass

    def order_limit_sell(self, currency: CoinnestCurrency, price: int, amount: float):
        pass

    def cancel_order(self, currency: CoinnestCurrency, order: Order):
        pass

    def get_order_info(self, currency: CoinnestCurrency, order_id: Order):
        pass

    def get_open_orders(self, currency: CoinnestCurrency):
        pass

    def get_past_trades(self, currency: CoinnestCurrency):
        pass

    @staticmethod
    def filter_successful_response(res: Response):
        if res.status_code != 200:
            raise ConnectionError("Network request has failed! (status code: %d)" % res.status_code)
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
                        raise CoinnestError(error_msg)

            return res_json
