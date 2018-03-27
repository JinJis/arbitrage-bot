import configparser
import urllib.parse
import logging
import sys
from datetime import datetime
from time import gmtime, strftime
import scipy.stats as st


class Global:
    USER_CONFIG_LOCATION = "config/conf_user.ini"
    DB_CONFIG_LOCATION = "config/conf_db.ini"
    DB_LOCAL_CONFIG_LOCATION = "config/conf_db_local.ini"
    COIN_FILTER_FOR_BALANCE = ("eth", "krw")

    @staticmethod
    def read_mongodb_uri(is_from_local: bool = False):
        config = configparser.ConfigParser()

        # read different file if the request is not from the remote server itself but from the local
        if is_from_local:
            config.read(Global.DB_LOCAL_CONFIG_LOCATION)
        else:
            config.read(Global.DB_CONFIG_LOCATION)

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
    def configure_default_root_logging():
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S",
                            stream=sys.stdout)

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
