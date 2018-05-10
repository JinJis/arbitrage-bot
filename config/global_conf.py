import os
import sys
import logging
import requests
import threading
import configparser
import urllib.parse
import scipy.stats as st
from pymongo.cursor import Cursor
from datetime import datetime
from itertools import zip_longest
from time import gmtime, strftime


class Global:
    USER_CONFIG_LOCATION = "config/conf_user.ini"
    LOCALHOST_DB_CONFIG_LOCATION = "config/conf_db_localhost.ini"
    REMOTE_DB_CONFIG_LOCATION = "config/conf_db_remote.ini"
    COIN_FILTER_FOR_BALANCE = ("eth", "btc", "bch", "krw")

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
    def get_z_score_for_probability(probability: float):
        # python calculates left/lower-tail probabilities by default
        # so we need to halve the excluded probability(`1 - prob`) before processing
        return st.norm.ppf(1 - (1 - probability) / 2)

    @staticmethod
    def get_unique_process_tag():
        # should only be called in initialization phase
        return "%s_%d" % (datetime.today().strftime("%Y%m%d%H%M"), os.getpid())

    @staticmethod
    def run_threaded(job_func, args=()):
        job_thread = threading.Thread(target=job_func, args=args)
        job_thread.start()

    @staticmethod
    def send_to_slack_channel(message: str):
        requests.post("https://hooks.slack.com/services/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", json={
            "text": message
        })

    @staticmethod
    def request_time_validation_on_cursor_count_diff(a_cursor: Cursor, b_cursor: Cursor):
        for a_item, b_item in zip_longest(a_cursor, b_cursor):
            a_rt = a_item["requestTime"]
            b_rt = b_item["requestTime"]
            if a_rt != b_rt:
                raise Exception("Please manually check and fix the data on DB: "
                                "a_cursor requestTime - %d, b_cursor requestTime - %d" % (a_rt, b_rt))

    @staticmethod
    def iso8601_to_unix(date_string):
        utc_dt = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        converted_time = int((utc_dt - datetime(1970, 1, 1)).total_seconds())
        return converted_time
