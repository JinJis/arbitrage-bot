import logging
from .global_conf import Global
from trader.market.market import Market
from pymongo import MongoClient
from pymongo.cursor import Cursor
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

    STREAMER_DB_NAME = "[RFAB]streamer"

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
    def get_process_db(cls, target_db_name: str) -> "Database":
        return cls.instance()[target_db_name][cls.p_db]

    @classmethod
    def get_streamer_db(cls) -> "Database":
        return cls.instance()[cls.STREAMER_DB_NAME]

    @classmethod
    def _async_insert(cls, target_col: Collection, doc: dict):
        Global.run_threaded(target_col.insert_one, [doc])

    @classmethod
    def _async_update(cls, target_col: Collection, _filter, _update):
        Global.run_threaded(target_col.update_one, [_filter, _update])

    @classmethod
    def async_trade_insert(cls, trade: dict):
        cls._async_insert(cls.get_process_db("[RFAB]result"), trade)

    @classmethod
    def async_order_insert(cls, order: dict):
        cls._async_insert(cls.get_process_db("[RFAB]result"), order)

    # This is for Stat Arbitrage Bot
    # @classmethod
    # def async_balance_insert(cls, balance: dict):
    #     cls._async_insert(cls.get_process_db()["balance"], balance)
    #
    # @classmethod
    # def async_order_update(cls, order: dict):
    #     cls._async_update(
    #         cls.get_process_db()["order"],
    #         {"order_id": order["order_id"]},
    #         {"$set": order}
    #     )

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
        # print("cursor count mm1: %d, mm2: %d" % (mm1_count, mm2_count))

        if mm1_count != mm2_count:
            logging.warning("Cursor count does not match! : mm1 %d, mm2 %d" % (mm1_count, mm2_count))
            logging.warning("should fix data...")
            # fixme: 이렇게 푸는거 ㅇㅋ?
            raise IndexError

        return mm1_cursor, mm2_cursor

    @staticmethod
    def match_request_time_in_orderbook_entry(mm1_col: Collection, mm2_col: Collection, start_time: int, end_time: int):

        mm1_cursor = mm1_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])
        mm2_cursor = mm2_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        mm1_count = mm1_cursor.count()
        mm2_count = mm2_cursor.count()

        if mm1_count > mm2_count:
            ctrl_cursor = mm1_cursor
            ctrl_data_count = mm1_count

            target_cur = mm2_cursor
            target_col = mm2_col

        else:
            ctrl_cursor = mm2_cursor

            ctrl_data_count = mm2_count

            target_cur = mm1_cursor
            target_col = mm1_col

        # get first nearest request time from control db
        first_ctrl_rq = ctrl_cursor[0]["requestTime"]

        # first target requestTime
        first_trgt_rq = target_cur[0]["requestTime"]
        # second target requestTime
        second_trgt_rq = target_cur[1]["requestTime"]

        # calc difference between control reqTime and target reqTimes
        ctrl_first_trgt_first_diff = abs(first_ctrl_rq - first_trgt_rq)
        ctrl_first_trgt_second_diff = abs(first_ctrl_rq - second_trgt_rq)

        # if first in target is nearer to first in control, set first in target as starting point
        if ctrl_first_trgt_first_diff < ctrl_first_trgt_second_diff:
            trgt_start_rq = first_trgt_rq
        # if second in target is nearer to first in control, set second in target as starting point
        elif ctrl_first_trgt_first_diff > ctrl_first_trgt_second_diff:
            trgt_start_rq = second_trgt_rq
        else:
            raise Exception("Difference is same, please Manually check the database and fix!!")

        # get same count of data from target db with the starting point as start time and without end time
        trgt_data_set = target_col.find({"requestTime": {
            "$gte": trgt_start_rq
        }}).sort([("requestTime", 1)]).limit(ctrl_data_count)
        trgt_data_count = trgt_data_set.count(with_limit_and_skip=True)

        logging.info("ctrl count count: %d, trgt: %d" % (ctrl_data_count, trgt_data_count))
        assert (ctrl_data_count == trgt_data_count)

        last_index = ctrl_data_count - 1
        ctrl_last_rq = ctrl_cursor[last_index]["requestTime"]
        trgt_last_rq = trgt_data_set[last_index]["requestTime"]
        assert (abs(ctrl_last_rq - trgt_last_rq) < 3)

        # loop through both
        # update target's request time with control's request
        for ctrl_data, trgt_data in zip(ctrl_cursor, trgt_data_set):
            ctrl_rq = ctrl_data["requestTime"]
            trgt_rq = trgt_data["requestTime"]
            logging.info("ctrl_rqt: %d, trgt_rqt: %d" % (ctrl_rq, trgt_rq))
            if trgt_rq == ctrl_rq:
                continue
            SharedMongoClient._async_update(
                target_col,
                {"requestTime": trgt_rq},
                {"$set": {"requestTime": ctrl_rq}}
            )

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
