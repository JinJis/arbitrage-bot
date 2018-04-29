import configparser
from bson import Decimal128
from requests import Response
from config.global_conf import Global
from trader.market.order import Order
from .currency import GopaxCurrency
from .market_api import MarketApi


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
        res_json = self.filter_succesful_response(res)

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
        res_json = self.filter_succesful_response(res)

        # normalize asks
        _asks = res_json["ask"]
        asks = list()
        for _ask in _asks[:20]:
                ask = {
                    "price": Decimal128(str(_ask[1])),
                    "amount": Decimal128(str(_ask[2]))
                }
                asks.append(ask)

        # normalize bids
        _bids = res_json["bid"]
        bids = list()
        for _bid in _bids[:20]:
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

    def get_order_info(self, currency: GopaxCurrency, order_id: str):
        super().get_order_info(currency, order_id)

    def get_balance(self):
        super().get_balance()

    def get_open_orders(self, currency: GopaxCurrency):
        super().get_open_orders(currency)

    def cancel_order(self, currency: GopaxCurrency, order: Order):
        super().cancel_order(currency, order)

    def order_limit_buy(self, currency: GopaxCurrency, price: int, amount: float):
        super().order_limit_buy(currency, price, amount)

    def order_limit_sell(self, currency: GopaxCurrency, price: int, amount: float):
        super().order_limit_sell(currency, price, amount)

    def get_past_trades(self, currency: GopaxCurrency):
        super().get_past_trades(currency)

    @staticmethod
    def filter_succesful_response(res: Response):
        if res.status_code != 200:
            raise Exception("Network request has failed! (status code: %d)" % res.status_code)
        else:
            return res.json()
