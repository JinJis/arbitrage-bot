from abc import abstractmethod
from pymongo import MongoClient
from config.global_conf import Global
from collector.collector import Collector
from api.bithumb_api import BithumbApi, BithumbCurrency
from api.okcoin_api import OkcoinApi, OkcoinCurrency
from api.coinnest_api import CoinnestApi, CoinnestCurrency
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
        bithumb_db = db_client["bithumb"]
        okcoin_db = db_client["okcoin"]
        coinnest_db = db_client["coinnest"]

        # init api
        bithumb_api = BithumbApi.instance(True)
        okcoin_api = OkcoinApi.instance(True)
        coinnest_api = CoinnestApi.instance(True)

        # init currency
        bithumb_currency = BithumbCurrency[currency.upper()]
        okcoin_currency = OkcoinCurrency[currency.upper()]
        coinnest_currency = CoinnestCurrency[currency.upper()]

        # init collector
        self.bt_collector = Collector(
            bithumb_api, bithumb_currency, bithumb_db
        )
        self.oc_collector = Collector(
            okcoin_api, okcoin_currency, okcoin_db
        )
        self.cn_collector = Collector(
            coinnest_api, coinnest_currency, coinnest_db
        )

    @abstractmethod
    def _actual_run_in_loop(self):
        pass
