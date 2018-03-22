import configparser
import urllib.parse


class Global:
    USER_CONFIG_LOCATION = "config/conf_user.ini"
    DB_CONFIG_LOCATION = "config/conf_db.ini"
    TARGET_COIN_FOR_BALANCE = ("btc", "eth", "krw")

    @staticmethod
    def read_mongodb_uri():
        config = configparser.ConfigParser()
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
