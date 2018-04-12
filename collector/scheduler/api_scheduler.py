from abc import abstractmethod
from pymongo import MongoClient
from config.global_conf import Global
from collector.collector import Collector
from api.korbit_api import KorbitApi, KorbitCurrency
from api.coinone_api import CoinoneApi, CoinoneCurrency
from collector.scheduler.base_scheduler import BaseScheduler


class ApiScheduler(BaseScheduler):
    def __init__(self, currency: str, should_use_localhost_db: bool = True):
        # make sure currency is in lower-case format
        if not currency.islower():
            raise Exception("<currency> parameter should be a lower-cased symbol of the target currency!")
        super().__init__()

        # init db
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db)
        db_client = MongoClient(mongodb_uri)
        coinone_db = db_client["coinone"]
        korbit_db = db_client["korbit"]

        # init api
        coinone_api = CoinoneApi.instance(True)
        korbit_api = KorbitApi.instance(True)

        # init currency
        coinone_currency = CoinoneCurrency[currency.upper()]
        korbit_currency = KorbitCurrency[currency.upper()]

        # init collector
        self.kb_collector = Collector(
            korbit_api, korbit_currency, korbit_db
        )
        self.co_collector = Collector(
            coinone_api, coinone_currency, coinone_db
        )

    @abstractmethod
    def _actual_run_in_loop(self):
        pass
