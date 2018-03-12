from .market_api import Machine
import requests
import time
import configparser
import base64
import json
import hashlib
import hmac


class CoinOneMachine(Machine):
    BASE_API_URL = "https://api.coinone.co.kr"
    TRADE_CURRENCY_TYPE = ["btc", "eth", "etc", "bch", "qtum", "krw", "xrp", "iota", "ltc"]

    def __init__(self, access_token=None, secret_key=None, username=None):
        if access_token is None or secret_key is None or username is None:
            raise Exception("Need to access token or secret_key.")
        self.access_token = access_token
        self.secret_key = secret_key
        self.username = username

    def get_username(self):
        return self.username

    def get_nonce(self):
        return int(time.time())

    def get_token(self):
        if self.access_token is not None:
            return self.access_token
        else:
            raise Exception("Need to set_token")

    def set_token(self, grant_type="refresh_token"):
        token_api_path = "/oauth/refresh_token/"
        url_path = self.BASE_API_URL + token_api_path
        "Maybe coinone token expire time is longer than korbit."
        self.expire = 3600
        if grant_type == "refresh_token":
            headers = {"content-type": "application/x-www-form-urlencoded"}
            data = {"access_token": self.access_token}
            config = configparser.ConfigParser()
            config.read('conf/config.ini')
            res = requests.post(url_path, headers=headers, data=data)
            result = res.json()
            self.access_token = result["accessToken"]
            config["COINONE"]["access_token"] = self.access_token
            with open('conf/config.ini', 'w') as configfile:
                config.write(configfile)
        else:
            config = configparser.ConfigParser()
            config.read('conf/config.ini')
            self.access_token = config['COINONE']['access_token']
        "coinone doesn't have refresh_token. you can get access_token if you return old token"
        return self.expire, self.access_token, self.access_token

    def get_ticker(self, currency_type=None):
        ticker_api_path = '/ticker/'
        url_path = self.BASE_API_URL + ticker_api_path
        params = {"currency": currency_type}
        res = requests.get(url_path, params=params)
        response_json = res.json()
        result = {}
        result["timestamp"] = str(response_json["timestamp"])
        result["last"] = response_json["last"]
        result["high"] = response_json["high"]
        result["low"] = response_json["low"]
        result["volume"] = response_json["volume"]
        return result

    def get_filled_orders(self, currency_type=None, per="minute"):
        pass

    def get_signature(self, encoded_payload, secret_key):
        signature = hmac.new(secret_key, encoded_payload, hashlib.sha512);
        return signature.hexdigest()

    def get_wallet_status(self):
        """
        Get wallet_status
        """
        time.sleep(1)
        wallet_status_api_path = "/v2/account/balance"
        url_path = self.BASE_API_URL + wallet_status_api_path
        payload = {
            "access_token": self.access_token,
            'nonce': self.get_nonce()
        }
        dumped_json = json.dumps(payload)
        encoded_payload = base64.b64encode(dumped_json.encode('utf-8'))

        headers = {'Content-type': 'application/json',
                   'X-COINONE-PAYLOAD': encoded_payload,
                   'X-COINONE-SIGNATURE': self.get_signature(encoded_payload, self.secret_key.encode('utf-8'))}

        res = requests.post(url_path, headers=headers, data=payload)
        result = res.json()
        wallet_status = {}
        for currency in self.TRADE_CURRENCY_TYPE:
            wallet_status[currency] = result[currency]
        return wallet_status

    def get_list_my_orders(self, currency_type=None):
        list_api_path = "/v2/order/limit_orders/"
        url_path = self.BASE_API_URL + list_api_path
        payload = {
            "access_token": self.access_token,
            "currency": currency_type,
            'nonce': self.get_nonce()
        }
        dumped_json = json.dumps(payload)
        encoded_payload = base64.b64encode(dumped_json.encode('utf-8'))

        headers = {'Content-type': 'application/json',
                   'X-COINONE-PAYLOAD': encoded_payload,
                   'X-COINONE-SIGNATURE': self.get_signature(encoded_payload, self.secret_key.encode('utf-8'))}

        res = requests.post(url_path, headers=headers, data=payload)
        result = res.json()
        return result

    def get_my_order_status(self, currency_type=None, order_id=None):
        """
        get list my transaction history
        """
        list_api_path = "/v2/order/order_info/"
        url_path = self.BASE_API_URL + list_api_path
        payload = {
            "access_token": self.access_token,
            "currency": currency_type,
            "order_id": order_id,
            'nonce': self.get_nonce()
        }
        dumped_json = json.dumps(payload)
        encoded_payload = base64.b64encode(dumped_json.encode('utf-8'))

        headers = {'Content-type': 'application/json',
                   'X-COINONE-PAYLOAD': encoded_payload,
                   'X-COINONE-SIGNATURE': self.get_signature(encoded_payload, self.secret_key.encode('utf-8'))}

        res = requests.post(url_path, headers=headers, data=payload)
        result = res.json()
        return result

    def buy_order(self, currency_type=None, price=None, qty=None, order_type="limit"):
        """
        buy_coin_order
        """
        if order_type != "limit":
            raise Exception("Coinone order type support only limit.")
        time.sleep(1)
        buy_limit_api_path = "/v2/order/limit_buy/"
        url_path = self.BASE_API_URL + buy_limit_api_path
        payload = {
            "access_token": self.access_token,
            "price": int(price),
            "qty": float(qty),
            "currency": currency_type,
            'nonce': self.get_nonce()
        }
        dumped_json = json.dumps(payload)
        encoded_payload = base64.b64encode(dumped_json.encode('utf-8'))

        headers = {'Content-type': 'application/json',
                   'X-COINONE-PAYLOAD': encoded_payload,
                   'X-COINONE-SIGNATURE': self.get_signature(encoded_payload, self.secret_key.encode('utf-8'))}

        res = requests.post(url_path, headers=headers, data=payload)
        result = res.json()
        return result

    def sell_order(self, currency_type=None, price=None, qty=None, order_type="limit"):
        """
        sell_coin_order
        """
        if order_type != "limit":
            raise Exception("Coinone order type support only limit.")
        time.sleep(1)
        sell_limit_api_path = "/v2/order/limit_sell/"
        url_path = self.BASE_API_URL + sell_limit_api_path
        payload = {
            "access_token": self.access_token,
            "price": int(price),
            "qty": float(qty),
            "currency": currency_type,
            'nonce': self.get_nonce()
        }
        dumped_json = json.dumps(payload)
        encoded_payload = base64.b64encode(dumped_json.encode('utf-8'))

        headers = {'Content-type': 'application/json',
                   'X-COINONE-PAYLOAD': encoded_payload,
                   'X-COINONE-SIGNATURE': self.get_signature(encoded_payload, self.secret_key.encode('utf-8'))}

        res = requests.post(url_path, headers=headers, data=payload)
        result = res.json()
        return result

    def cancel_order(self, currency_type=None, price=None, qty=None, order_type=None, order_id=None):
        """
        cancel_coin_order
        """
        if currency_type is None or price is None or qty is None or order_type is None or order_id is None:
            raise Exception("Need to parameter")
        time.sleep(1)
        cancel_api_path = "/v2/order/cancel/"
        url_path = self.BASE_API_URL + cancel_api_path
        if order_type == "sell":
            is_ask = 1
        else:
            is_ask = 0
        payload = {
            "access_token": self.access_token,
            "order_id": order_id,
            "price": int(price),
            "qty": float(qty),
            "currency": currency_type,
            "is_ask": is_ask,
            'nonce': self.get_nonce()
        }
        dumped_json = json.dumps(payload)
        encoded_payload = base64.b64encode(dumped_json.encode('utf-8'))

        headers = {'Content-type': 'application/json',
                   'X-COINONE-PAYLOAD': encoded_payload,
                   'X-COINONE-SIGNATURE': self.get_signature(encoded_payload, self.secret_key.encode('utf-8'))}

        res = requests.post(url_path, headers=headers, data=payload)
        result = res.json()
        return result

    def __repr__(self):
        return "(CoinOne %s)" % self.username

    def __str__(self):
        return str("CoinOne")
