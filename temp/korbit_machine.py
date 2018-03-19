import requests
import time
from machine.base_machine import Machine
import configparser


class KorbitMachine(Machine):
    BASE_API_URL = "https://api.korbit.co.kr"
    TRADE_CURRENCY_TYPE = ["btc", "bch", "btg", "eth", "etc", "xrp", "krw"]

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('conf/config.ini')
        self.CLIENT_ID = config['KORBIT']['client_id']
        self.CLIENT_SECRET = config['KORBIT']['client_secret']
        self.USER_NAME = config['KORBIT']['username']
        self.PASSWORD = config['KORBIT']['password']
        self.access_token = None
        self.refresh_token = None
        self.token_type = None

    def get_username(self):
        return self.USER_NAME

    def get_nonce(self):
        return str(int(time.time()))

    def get_token(self):
        if self.access_token is not None:
            return self.access_token
        else:
            raise Exception("Need to set_token")

    def set_token(self, grant_type="password"):
        token_api_path = "/v1/oauth2/access_token"

        url_path = self.BASE_API_URL + token_api_path
        if grant_type == "password":
            data = {
                "client_id": self.CLIENT_ID,
                "client_secret": self.CLIENT_SECRET,
                "username": self.USER_NAME,
                "password": self.PASSWORD,
                "grant_type": grant_type
            }
        elif grant_type == "refresh_token":
            data = {
                "client_id": self.CLIENT_ID,
                "client_secret": self.CLIENT_SECRET,
                "refresh_token": self.refresh_token,
                "grant_type": grant_type
            }
        else:
            raise Exception("Unexpected grant_type")

        res = requests.post(url_path, data=data)
        result = res.json()
        self.access_token = result["access_token"]
        self.token_type = result["token_type"]
        self.refresh_token = result["refresh_token"]
        self.expire = result["expires_in"]
        return self.expire, self.access_token, self.refresh_token

    def get_ticker(self, currency_type=None):
        if currency_type is None:
            raise Exception('Need to currency type')
        time.sleep(1)
        params = {'currency_pair': currency_type}
        ticker_api_path = "/v1/ticker/detailed"
        url_path = self.BASE_API_URL + ticker_api_path
        res = requests.get(url_path, params=params)
        response_json = res.json()
        result = {}
        result["timestamp"] = str(response_json["timestamp"])
        result["last"] = response_json["last"]
        result["bid"] = response_json["bid"]
        result["ask"] = response_json["ask"]
        result["high"] = response_json["high"]
        result["low"] = response_json["low"]
        result["volume"] = response_json["volume"]
        return result

    def get_filled_orders(self, currency_type=None, per="minute"):
        if currency_type is None:
            raise Exception("Need to currency_type")
        time.sleep(1)
        payload = {'currency_pair': currency_type, 'time': per}
        orders_api_path = "/v1/transactions"
        url_path = self.BASE_API_URL + orders_api_path
        res = requests.get(url_path, params=payload)
        result = res.json()
        return result

    def get_constants(self):
        time.sleep(1)
        constants_api_path = "/v1/constants"
        url_path = self.BASE_API_URL + constants_api_path
        res = requests.get(url_path)
        result = res.json()
        self.constants = result
        return result

    def get_wallet_status(self):
        time.sleep(1)
        wallet_status_api_path = "/v1/user/balances"
        url_path = self.BASE_API_URL + wallet_status_api_path
        headers = {"Authorization": "Bearer " + self.access_token}
        res = requests.get(url_path, headers=headers)
        result = res.json()
        wallet_status = {currency: dict(avail=result[currency]["available"]) for currency in self.TRADE_CURRENCY_TYPE}
        for item in self.TRADE_CURRENCY_TYPE:
            wallet_status[item]["balance"] = str(
                float(result[item]["trade_in_use"]) + float(result[item]["withdrawal_in_use"]))
        return wallet_status

    def get_list_my_orders(self, currency_type=None):
        if currency_type is None:
            raise Exception("Need to currency_type")
        time.sleep(1)
        params = {'currency_pair': currency_type}
        list_order_api_path = "/v1/user/orders/open"
        url_path = self.BASE_API_URL + list_order_api_path
        headers = {"Authorization": "Bearer " + self.access_token}
        res = requests.get(url_path, headers=headers, params=params)
        result = res.json()
        return result

    def get_my_order_status(self, currency_type=None, order_id=None):
        if currency_type is None or order_id is None:
            raise Exception("Need to currency_pair and order id")
        time.sleep(1)
        list_transaction_api_path = "/v1/user/orders"
        url_path = self.BASE_API_URL + list_transaction_api_path
        headers = {"Authorization": "Bearer " + self.access_token}
        params = {"currency_pair": currency_type, "id": order_id}
        res = requests.get(url_path, headers=headers, params=params)
        result = res.json()
        return result

    def buy_order(self, currency_type=None, price=None, qty=None, order_type="limit"):
        time.sleep(1)
        if currency_type is None or price is None or qty is None:
            raise Exception("Need to param")
        buy_order_api_path = "/v1/user/orders/buy"
        url_path = self.BASE_API_URL + buy_order_api_path
        headers = {"Authorization": "Bearer " + self.access_token}
        data = {"currency_pair": currency_type,
                "type": order_type,
                "price": price,
                "coin_amount": qty,
                "nonce": self.get_nonce()}
        res = requests.post(url_path, headers=headers, data=data)
        result = res.json()
        return result

    def sell_order(self, currency_type=None, price=None, qty=None, order_type="limit"):
        time.sleep(1)
        if price is None or qty is None or currency_type is None:
            raise Exception("Need to params")
        if order_type != "limit":
            raise Exception("Check order type")
        sell_order_api_path = "/v1/user/orders/sell"
        url_path = self.BASE_API_URL + sell_order_api_path
        headers = {"Authorization": "Bearer " + self.access_token}
        data = {"currency_pair": currency_type,
                "type": order_type,
                "price": price,
                "coin_amount": qty,
                "nonce": self.get_nonce()}
        res = requests.post(url_path, headers=headers, data=data)
        result = res.json()
        return result

    def cancel_order(self, currency_type=None, price=None, qty=None, order_type=None, order_id=None):
        time.sleep(1)
        if currency_type is None or order_id is None:
            raise Exception("Need to params")
        cancel_order_api_path = "/v1/user/orders/cancel"
        url_path = self.BASE_API_URL + cancel_order_api_path
        headers = {"Authorization": "Bearer " + self.access_token}
        data = {"currency_pair": currency_type,
                "id": order_id,
                "nonce": self.get_nonce()}
        res = requests.post(url_path, headers=headers, data=data)
        result = res.json()
        return result

    def __repr__(self):
        return "(Korbit %s)" % self.USER_NAME

    def __str__(self):
        return str("Korbit")
