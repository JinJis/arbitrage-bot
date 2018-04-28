import time
import configparser
from bson import decimal128
from requests import Response
from datetime import datetime
from .market_api import MarketApi
from .currency import GopaxCurrency
from config.global_conf import Global
from trader.market.order import Order, OrderStatus


class GopaxAPI(MarketApi):
    BASE_URL = "https://api.gopax.co.kr"

    def __init__(self, is_public_access_only=False):
        super().__init__(is_public_access_only)
        if not is_public_access_only:
            # set instance wide config
            self._config = configparser.ConfigParser()
            self._config.read(Global.USER_CONFIG_LOCATION)

            # set initial api_token & secret_key
            self._api_token = self._config["GOPAX"]["api_token"]
            self._secret_key = self._config["GOPAX"]["secret_key"]

    def get_ticker(self, currency: GopaxCurrency):
        res = self._session.get(self.BASE_URL + "/trading-pairs/%s/stats" % currency.value)
        res_json = self.filter_successful_response(res)

        # reformat result
        result = {
            "timestamp": res_json["time"]


        }

