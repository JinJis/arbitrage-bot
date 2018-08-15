import logging
from .global_conf import Global
from trader.market.market import Market
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


# note that MongoClient is itself thread-safe
# see [http://api.mongodb.com/python/current/faq.html#is-pymongo-thread-safe]
class SharedMongoClient:
    COINONE_DB_NAME = "coinone"
    KORBIT_DB_NAME = "korbit"
    GOPAX_DB_NAME = "gopax"
    BITHUMB_DB_NAME = "bithumb"
    OKCOIN_DB_NAME = "okcoin"
    COINNEST_DB_NAME = "coinnest"

    __singleton_instance = None

    # target db name for current process
    p_db = Global.get_unique_process_tag()

    """
        [collection name]
        trade, order, balance
    """

    def __init__(self):
        raise Exception("Class method `initialize` or `instance` should be called instead!")

    @classmethod
    def initialize(cls, should_use_localhost_db: bool = True):
        cls.__singleton_instance = MongoClient(Global.read_mongodb_uri(should_use_localhost_db))

    @classmethod
    def instance(cls):
        if cls.__singleton_instance is None:
            raise Exception("SharedMongoClient has never been initialized! Call `initialize` to init first.")
        return cls.__singleton_instance

    @classmethod
    def get_coinone_db(cls) -> "Database":
        return cls.instance()[cls.COINONE_DB_NAME]

    @classmethod
    def get_korbit_db(cls) -> "Database":
        return cls.instance()[cls.KORBIT_DB_NAME]

    @classmethod
    def get_gopax_db(cls) -> "Database":
        return cls.instance()[cls.GOPAX_DB_NAME]

    @classmethod
    def get_bithumb_db(cls) -> "Database":
        return cls.instance()[cls.BITHUMB_DB_NAME]

    @classmethod
    def get_okcoin_db(cls) -> "Database":
        return cls.instance()[cls.OKCOIN_DB_NAME]

    @classmethod
    def get_coinnest_db(cls) -> "Database":
        return cls.instance()[cls.COINNEST_DB_NAME]

    @classmethod
    def get_process_db(cls) -> "Database":
        return cls.instance()[cls.p_db]

    @classmethod
    def _async_insert(cls, target_col: Collection, doc: dict):
        Global.run_threaded(target_col.insert_one, [doc])

    @classmethod
    def _async_update(cls, target_col: Collection, _filter, _update):
        Global.run_threaded(target_col.update_one, [_filter, _update])

    @classmethod
    def async_trade_insert(cls, trade: dict):
        cls._async_insert(cls.get_process_db()["trade"], trade)

    @classmethod
    def async_order_insert(cls, order: dict):
        cls._async_insert(cls.get_process_db()["order"], order)

    @classmethod
    def async_balance_insert(cls, balance: dict):
        cls._async_insert(cls.get_process_db()["balance"], balance)

    @classmethod
    def async_order_update(cls, order: dict):
        cls._async_update(
            cls.get_process_db()["order"],
            {"order_id": order["order_id"]},
            {"$set": order}
        )

    @classmethod
    def get_target_db(cls, market_tag: Market):
        method_name = {
            Market.VIRTUAL_COINONE: "get_coinone_db",
            Market.VIRTUAL_KORBIT: "get_korbit_db",
            Market.VIRTUAL_GOPAX: "get_gopax_db",
            Market.VIRTUAL_BITHUMB: "get_bithumb_db",
            Market.VIRTUAL_OKCOIN: "get_okcoin_db",
            Market.VIRTUAL_COINNEST: "get_coinnest_db"
        }[market_tag]
        return getattr(cls, method_name)()

    @staticmethod
    def get_data_from_db(mm1_data_col: Collection, mm2_data_col: Collection, start_time: int, end_time: int):
        mm1_cursor = mm1_data_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])
        mm2_cursor = mm2_data_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        mm1_count = mm1_cursor.count()
        mm2_count = mm2_cursor.count()
        if mm1_count != mm2_count:
            logging.warning("Cursor count does not match! : mm1 %d, mm2 %d" % (mm1_count, mm2_count))
            logging.info("Now validating data...")
            Global.request_time_validation_on_cursor_count_diff(mm1_cursor, mm2_cursor)

        return mm1_cursor, mm2_cursor

    @staticmethod
    def get_target_col(market_tag: Market, target_coin: str):
        method_name = {
            Market.VIRTUAL_COINONE: "get_coinone_db",
            Market.VIRTUAL_KORBIT: "get_korbit_db",
            Market.VIRTUAL_GOPAX: "get_gopax_db",
            Market.VIRTUAL_BITHUMB: "get_bithumb_db",
            Market.VIRTUAL_OKCOIN: "get_okcoin_db",
            Market.VIRTUAL_COINNEST: "get_coinnest_db"
        }[market_tag]
        return getattr(SharedMongoClient, method_name)()[target_coin + "_orderbook"]
