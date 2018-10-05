import configparser
import itertools as it
import logging
import os
import sys
import threading
import urllib.parse
from datetime import datetime
from itertools import zip_longest
from time import gmtime, strftime

import pytz
import requests
import scipy.stats as st
from pymongo.cursor import Cursor




class Global:
    USER_CONFIG_LOCATION = "config/conf_user.ini"
    LOCALHOST_DB_CONFIG_LOCATION = "config/conf_db_localhost.ini"
    REMOTE_DB_CONFIG_LOCATION = "config/conf_db_remote.ini"
    MARKET_FEE_LOCATION = "config/conf_market_fee.ini"
    MIN_TRADING_COIN = "config/conf_min_trading_coin.ini"
    IYO_CONFIG_LOCATION = "config/conf_iyo_market.ini"
    SLICED_IYO_CONFIG_LOCATION = "config/conf_sliced_iyo_market.ini"
    RFAB_COMBINATION_CONFIG_LOCATION = "config/conf_rfab_combi.ini"
    COIN_FILTER_FOR_BALANCE = ("eth", "btc", "bch", "qtum", "xrp", "trx", "eos", "krw")

    SLACK_BOT_STATUS_URL = "https://hooks.slack.com/services/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"
    SLACK_BAL_STATUS_URL = "https://hooks.slack.com/services/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"
    SLACK_STREAM_STATUS_URL = "https://hooks.slack.com/services/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"
    SLACK_OTC_SCHEDUELR_URL = "https://hooks.slack.com/services/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"

    @staticmethod
    def read_mongodb_uri(should_use_localhost_db: bool = True):
        config = configparser.ConfigParser()

        # read different file if the request is not from the remote server itself but from the local
        if should_use_localhost_db:
            config.read(Global.LOCALHOST_DB_CONFIG_LOCATION)
        else:
            config.read(Global.REMOTE_DB_CONFIG_LOCATION)

        mongo = config["MONGO"]
        host = mongo["host"]
        port = mongo.getint("port")
        use_auth = mongo.getboolean("use_auth")

        if use_auth:
            username = urllib.parse.quote_plus(mongo["username"])
            password = urllib.parse.quote_plus(mongo["password"])
            return "mongodb://%s:%s@%s:%d" % (username, password, host, port)
        else:
            return "mongodb://%s:%d" % (host, port)

    @staticmethod
    def read_market_fee(exchange_name: str, is_taker_fee: bool) -> float:
        config = configparser.ConfigParser()
        config.read(Global.MARKET_FEE_LOCATION)

        # first check whether exchange name includes VIRTUAL and remove if any
        if "VIRTUAL_" in exchange_name:
            unified_exchge_name = exchange_name.replace("VIRTUAL_", "")
        else:
            unified_exchge_name = exchange_name

        # decide fee
        if is_taker_fee:
            fee = float(config[unified_exchge_name.upper()]["TAKER_FEE"])
        elif not is_taker_fee:
            fee = float(config[unified_exchge_name.upper()]["MAKER_FEE"])
        else:
            raise Exception("Please choose between TAKER or MAKER fee!")
        return fee

    @staticmethod
    def read_min_trading_coin(exchange_name: str, coin_name: str):
        config = configparser.ConfigParser()
        config.read(Global.MIN_TRADING_COIN)
        return float(config[exchange_name.upper()][coin_name])

    @staticmethod
    def read_min_order_digit(exchange_name: str):
        config = configparser.ConfigParser()
        config.read(Global.MIN_TRADING_COIN)
        return int(config[exchange_name.upper()]["min_digit"])

    @staticmethod
    def read_iyo_setting_config(target_currency: str):
        config = configparser.ConfigParser()
        config.read(Global.IYO_CONFIG_LOCATION)
        division = int(config["UNIVERSAL_SETTING"]["DIVISION"])
        depth = int(config["UNIVERSAL_SETTING"]["DEPTH"])
        consecution_time = int(config["UNIVERSAL_SETTING"]["consecution_time"])
        krw_seq_end = float(config["BALANCE_SETTING"]["KRW_SEQ_END"])
        coin_seq_end = float(config["BALANCE_SETTING"]["COIN_SEQ_END"])
        max_trade_coin_end = float(config["%s_SETTING" % target_currency.upper()]["MAX_TRADE_COIN_END"])
        threshold_end = int(config["%s_SETTING" % target_currency.upper()]["THRESHOLD_END"])
        appx_unit_coin_p = int(config["%s_SETTING" % target_currency.upper()]["APPX_UNIT_COIN_PRICE"])

        return {
            "division": division,
            "depth": depth,
            "consecution_time": consecution_time,
            "krw_seq_end": krw_seq_end,
            "coin_seq_end": coin_seq_end,
            "max_trade_coin_end": max_trade_coin_end,
            "threshold_end": threshold_end,
            "appx_unit_coin_price": appx_unit_coin_p
        }

    @staticmethod
    def read_sliced_iyo_setting_config(target_currency: str):
        sliced_iyo_config = configparser.ConfigParser()
        sliced_iyo_config.read(Global.SLICED_IYO_CONFIG_LOCATION)
        division = int(sliced_iyo_config["SLICED_SETTING"]["DIVISION"])
        depth = int(sliced_iyo_config["SLICED_SETTING"]["DEPTH"])
        consecution_time = int(sliced_iyo_config["SLICED_SETTING"]["CONSECUTION_TIME"])
        slicing_interval = int(sliced_iyo_config["SLICED_SETTING"]["SLICING_INTERVAL"])

        # for rest of infos, use original IYO config
        iyo_config = configparser.ConfigParser()
        iyo_config.read(Global.IYO_CONFIG_LOCATION)
        krw_seq_end = float(iyo_config["BALANCE_SETTING"]["KRW_SEQ_END"])
        coin_seq_end = float(iyo_config["BALANCE_SETTING"]["COIN_SEQ_END"])
        max_trade_coin_end = float(iyo_config["%s_SETTING" % target_currency.upper()]["MAX_TRADE_COIN_END"])
        threshold_end = int(iyo_config["%s_SETTING" % target_currency.upper()]["THRESHOLD_END"])
        appx_unit_coin_p = int(iyo_config["%s_SETTING" % target_currency.upper()]["APPX_UNIT_COIN_PRICE"])

        return {
            "division": division,
            "depth": depth,
            "consecution_time": consecution_time,
            "slicing_interval": slicing_interval,
            "krw_seq_end": krw_seq_end,
            "coin_seq_end": coin_seq_end,
            "max_trade_coin_end": max_trade_coin_end,
            "threshold_end": threshold_end,
            "appx_unit_coin_price": appx_unit_coin_p
        }

    @staticmethod
    def write_balance_seq_end_to_ini(krw_seq_end: float, coin_seq_end: float):
        config = configparser.ConfigParser()
        config.read(Global.IYO_CONFIG_LOCATION)
        config.set("BALANCE_SETTING", "KRW_SEQ_END", str(krw_seq_end))
        config.set("BALANCE_SETTING", "COIN_SEQ_END", str(coin_seq_end))
        with open(Global.IYO_CONFIG_LOCATION, 'w') as configfile:
            config.write(configfile)

    @staticmethod
    def write_iyo_config_by_target_currency(target_currency: str,
                                            max_trade_coin_end: float, threshold_end: int, appx_unit_coin_price: int):
        config = configparser.ConfigParser()
        config.read(Global.IYO_CONFIG_LOCATION)
        config.set("%s_SETTING" % target_currency.upper(), "max_trade_coin_end", str(max_trade_coin_end))
        config.set("%s_SETTING" % target_currency.upper(), "threshold_end", str(threshold_end))
        config.set("%s_SETTING" % target_currency.upper(), "appx_unit_coin_price", str(appx_unit_coin_price))
        with open(Global.IYO_CONFIG_LOCATION, 'w') as configfile:
            config.write(configfile)

    @staticmethod
    def get_avail_coin_in_list():
        config = configparser.ConfigParser()
        config.read(Global.RFAB_COMBINATION_CONFIG_LOCATION)
        result = []
        for exchange in config:
            if exchange == "DEFAULT":
                continue
            result.append(str(exchange).lower())
        return result

    @staticmethod
    def get_rfab_combination_tuples(target_currency: str):
        """
        :param target_currency: bch, btc, tron...
        :return: [('bithumb', 'coinone'), ('bithumb', 'okcoin')...]
        """
        config = configparser.ConfigParser()
        config.read(Global.RFAB_COMBINATION_CONFIG_LOCATION)
        target_config = config[target_currency.upper()]

        exchange_list = []
        for exchange in target_config.keys():
            if target_config[exchange] == "yes":
                exchange_list.append(exchange)
            else:
                continue

        return list(it.combinations(exchange_list, 2))

    @staticmethod
    def get_inner_ocat_combination(target_market: str, target_currency: str):
        all_combi_list = Global.get_rfab_combination_tuples(target_currency)
        inner_ocat_list = []
        for combi in all_combi_list:
            if target_market in combi:
                inner_ocat_list.append(combi)
        return inner_ocat_list

    @staticmethod
    def configure_default_root_logging(log_level: int = logging.INFO, should_log_to_file: bool = False):
        if not should_log_to_file:
            logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s",
                                datefmt="%Y-%m-%d %H:%M:%S", stream=sys.stdout)
        else:
            logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s",
                                datefmt="%Y-%m-%d %H:%M:%S", filename=("log/%s.log" % datetime.now()))

    @staticmethod
    def convert_local_datetime_to_epoch(datetime_str, timezone=None):
        # `datetime_str` should be in the format of "%Y.%m.%d %H:%M:%S", ex) "2018.03.25 10:00:00"

        if timezone == "cn":
            gmt = "+0800"
        elif timezone == "kr":
            gmt = "+0900"
        else:
            # default behavior is to use system timezone
            gmt = strftime("%z", gmtime())

        return int(datetime.strptime("%s GMT%s" % (datetime_str, gmt), "%Y.%m.%d %H:%M:%S GMT%z").timestamp())

    @staticmethod
    def convert_epoch_to_local_datetime(epoch_time: int, timezone=None):
        # `epoch_time` should be 10 digited number, ex) "1533890277"

        if timezone == "cn":
            tz = pytz.timezone('Asia/Beijing')
        elif timezone == "kr":
            tz = pytz.timezone('Asia/Seoul')
        else:
            # default behavior is to use system timezone
            tz = datetime.now().astimezone().tzinfo

        return str(datetime.fromtimestamp(epoch_time, tz).strftime('%Y.%m.%d %H:%M:%S'))

    @staticmethod
    def get_z_score_for_probability(probability: float):
        # python calculates left/lower-tail probabilities by default
        # so we need to halve the excluded probability(`1 - prob`) before processing
        return st.norm.ppf(1 - (1 - probability) / 2)

    @staticmethod
    def get_unique_process_tag():
        # should only be called in initialization phase
        return "[start]:%s_[process]:%d" % (datetime.today().strftime("%Y.%m.%d_%H:%M"), os.getpid())

    @staticmethod
    def run_threaded(job_func, args=()):
        job_thread = threading.Thread(target=job_func, args=args)
        job_thread.start()

    @staticmethod
    def send_to_slack_channel(target_url: str, message: str):
        requests.post(target_url, json={
            "text": message
        })

    @staticmethod
    def request_time_validation_on_cursor_count_diff(a_cursor: Cursor, b_cursor: Cursor):
        for a_item, b_item in zip_longest(a_cursor, b_cursor):
            a_rt = a_item["requestTime"]
            b_rt = b_item["requestTime"]
            if a_rt != b_rt:
                raise IndexError("Please manually check and fix the data on DB: "
                                 "a_cursor requestTime - %d, b_cursor requestTime - %d" % (a_rt, b_rt))

    @staticmethod
    def iso8601_to_unix(date_string):
        utc_dt = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        converted_time = int((utc_dt - datetime(1970, 1, 1)).total_seconds())
        return converted_time

    @staticmethod
    def find_middle_of_list(input_list):
        if len(input_list) == 0:
            raise Exception("The input list should have at least one value embedded!")

        middle = float(len(input_list)) / 2
        if middle % 2 != 0:
            return input_list[int(middle - .5)]
        else:
            return input_list[int(middle)]

    @staticmethod
    def get_market_manager(name: str):
        from trader.market_manager.bithumb_market_manager import BithumbMarketManager
        from trader.market_manager.coinnest_market_manager import CoinnestMarketManager
        from trader.market_manager.coinone_market_manager import CoinoneMarketManager
        from trader.market_manager.gopax_market_manager import GopaxMarketManager
        from trader.market_manager.korbit_market_manager import KorbitMarketManager
        from trader.market_manager.okcoin_market_manager import OkcoinMarketManager
        return {
            "bithumb": BithumbMarketManager,
            "coinone": CoinoneMarketManager,
            "korbit": KorbitMarketManager,
            "gopax": GopaxMarketManager,
            "okcoin": OkcoinMarketManager,
            "coinnest": CoinnestMarketManager
        }[name.lower()]()
