from abc import abstractmethod
from pymongo import MongoClient
from config.global_conf import Global
from collector.collector import Collector
from api.gopax_api import GopaxAPI, GopaxCurrency
from collector.scheduler.base_scheduler import BaseScheduler


class ApiScheduler2(BaseScheduler):
    def __init__(self, currency: str, should_use_localhost_db: bool = False):
        # make sure currency is in lower-case format
        if not currency.islower():
            raise Exception("<currency> parameter should be a lower-cased symbol of the target currency!")
        super().__init__()

        # init db
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db)
        db_client = MongoClient(mongodb_uri)
        gopax_db = db_client["gopax"]

        # init api
        gopax_api = GopaxAPI.instance(True)

        # init currency
        gopax_currency = GopaxCurrency[currency.upper()]

        # init collector
        self.go_collector = Collector(
            gopax_api, gopax_currency, gopax_db
        )

    @abstractmethod
    def _actual_run_in_loop(self):
        pass
