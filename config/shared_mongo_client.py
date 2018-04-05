from .global_conf import Global
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


# note that MongoClient is itself thread-safe
# see [http://api.mongodb.com/python/current/faq.html#is-pymongo-thread-safe]
class SharedMongoClient:
    COINONE_DB_NAME = "coinone"
    KORBIT_DB_NAME = "korbit"

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
    def get_pdb_order_col(cls) -> "Collection":
        return cls.instance()[cls.p_db]["order"]

    @classmethod
    def get_process_db(cls) -> "Database":
        return cls.instance()[cls.p_db]

    @classmethod
    def get_coinone_db(cls) -> "Database":
        return cls.instance()[cls.COINONE_DB_NAME]

    @classmethod
    def get_korbit_db(cls) -> "Database":
        return cls.instance()[cls.KORBIT_DB_NAME]
