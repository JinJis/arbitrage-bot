import logging
import time

from bson.objectid import ObjectId

from config.shared_mongo_client import SharedMongoClient
from trader.market_manager.market_manager import MarketManager


class BalanceUpdater:
    interval_time = 5

    def __init__(self, target_currency, mm1: MarketManager, mm2: MarketManager, mongo_id: ObjectId, is_test: bool):
        if is_test:
            self.bal_updater_col = SharedMongoClient.get_test_streamer_db()["balance_updater"]
        if not is_test:
            self.bal_updater_col = SharedMongoClient.get_streamer_db()["balane_updater"]

        self.mm1 = mm1
        self.mm2 = mm2
        self._id = mongo_id
        self.target_currency = target_currency

    def update_balance_looper(self):

        while True:

            loop_start = time.time()

            try:
                # update balance by API call
                self.mm1.update_balance()
                self.mm2.update_balance()

                mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
                mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
                mm1_coin_bal = float(self.mm1.balance.get_available_coin(self.target_currency))
                mm2_coin_bal = float(self.mm2.balance.get_available_coin(self.target_currency))

                # update MongoDB data with designated _id
                self.bal_updater_col.update({'_id': self._id}, {
                    "$set": {
                        "mm1.krw": mm1_krw_bal,
                        "mm1.coin": mm1_coin_bal,
                        "mm2.krw": mm2_krw_bal,
                        "mm2.coin": mm2_coin_bal,
                        "total.krw": mm1_krw_bal + mm2_krw_bal,
                        "total.coin": mm1_coin_bal + mm2_coin_bal
                    }}, upsert=True)
                logging.warning("success")

            except Exception as e:
                logging.error(e)

            self.sleep_time_handler(loop_start)

    @staticmethod
    def sleep_time_handler(loop_start: float):
        loop_spent = time.time() - loop_start
        time_to_sleep = BalanceUpdater.interval_time - loop_spent
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
