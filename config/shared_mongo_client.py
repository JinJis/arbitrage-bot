from pymongo import MongoClient
from .global_conf import Global


# note that MongoClient is thread-safe
# see [http://api.mongodb.com/python/current/faq.html#is-pymongo-thread-safe]
class SharedMongoClient:
    __singleton_instance = None

    # target db name for current process
    p_db = Global.get_unique_process_tag()

    """
        [collection name]
        trade, order, balance
    """

    @classmethod
    def initialize(cls, should_use_localhost_db: bool = True):
        cls.__singleton_instance = MongoClient(Global.read_mongodb_uri(should_use_localhost_db))

    @classmethod
    def instance(cls):
        if cls.__singleton_instance is None:
            raise Exception("SharedMongoClient has never been initialized! Call `initialize` to init first.")
        return cls.__singleton_instance
