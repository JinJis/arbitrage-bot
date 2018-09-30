import logging
import time

from trader.market_manager.market_manager import MarketManager
from trader.user_manager.usermanager import UserManager


class BalanceUpdater:
    interval_time = 3

    def __init__(self, _user_id: str, target_currency, mm1: MarketManager, mm2: MarketManager):

        self._user_id = _user_id
        self.mm1 = mm1
        self.mm2 = mm2
        self.target_currency = target_currency

        self.bal_tracker_query_key = "balance_tracker.%s-%s-%s" % (
            self.target_currency, mm1.get_market_name().lower(), mm2.get_market_name().lower())

    def update_balance_looper(self):

        loop_count = 1
        while True:
            # todo: 여기서 settlement이면 할 작업

            loop_start_time = time.time()

            try:
                # update balance by API call
                self.mm1.update_balance()
                self.mm2.update_balance()

                mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
                mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
                mm1_coin_bal = float(self.mm1.balance.get_available_coin(self.target_currency))
                mm2_coin_bal = float(self.mm2.balance.get_available_coin(self.target_currency))

                bal_to_append = {
                    "krw": {
                        "mm1": mm1_krw_bal,
                        "mm2": mm2_krw_bal,
                        "total": mm1_krw_bal + mm2_krw_bal
                    },
                    "coin": {
                        "mm1": mm1_coin_bal,
                        "mm2": mm2_coin_bal,
                        "total": mm1_coin_bal + mm2_coin_bal
                    }
                }

                if loop_count == 1:
                    # if initiation
                    UserManager().find_user_and_update_streamer(
                        user_id=self._user_id, query_dict={
                            self.bal_tracker_query_key: {
                                "time": int(loop_start_time),
                                "init_bal": bal_to_append,
                                "current_bal": bal_to_append
                            }})
                    # todo: trade history에 initiation이라고 넣어서 나중에 엑셀로 뽑을수 있게끔!

                else:
                    # after initiation
                    UserManager().find_user_and_update_streamer(
                        user_id=self._user_id, query_dict={
                            self.bal_tracker_query_key + ".time": int(loop_start_time),
                            self.bal_tracker_query_key + ".current_bal": bal_to_append
                        })

            except Exception as e:
                logging.error(e)

            logging.warning("%d: Balance updater success" % loop_count)
            self.sleep_time_handler(loop_start_time)
            loop_count += 1

    @staticmethod
    def sleep_time_handler(loop_start: float):
        loop_spent = time.time() - loop_start
        time_to_sleep = BalanceUpdater.interval_time - loop_spent
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
