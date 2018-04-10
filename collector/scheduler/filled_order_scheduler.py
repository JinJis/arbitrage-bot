from collector.filled_order_collector import FilledOrderCollector
from collector.scheduler.base_scheduler import BaseScheduler
from config.global_conf import Global
from pymongo import MongoClient
from api.coinone_api import CoinoneApi, CoinoneCurrency
from api.korbit_api import KorbitApi, KorbitCurrency


class FilledOrderScheduler(BaseScheduler):
    def __init__(self, currency: str, should_use_localhost_db: bool = True):
        # make sure currency is in lower-case format
        if not currency.islower():
            raise Exception("<currency> parameter should be a lower-cased symbol of the target currency!")

        super().__init__()
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db)
        db_client = MongoClient(mongodb_uri)
        coinone_db = db_client["coinone"]
        korbit_db = db_client["korbit"]
        coinone_api = CoinoneApi.instance(True)
        korbit_api = KorbitApi.instance(True)
        coinone_currency = CoinoneCurrency[currency.upper()]
        korbit_currency = KorbitCurrency[currency.upper()]
        filled_orders_col_name = currency + "_filled_orders"

        self.kb_collector = FilledOrderCollector(korbit_api, korbit_currency, korbit_db[filled_orders_col_name])

    @BaseScheduler.interval_waiter(5)
    def _actual_run_in_loop(self):
        Global.run_threaded(self.kb_collector.collect_filled_orders)


if __name__ == "__main__":
    FilledOrderScheduler().run()
