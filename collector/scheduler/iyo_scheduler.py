import sys
import time
import logging
from config.global_conf import Global
from trader.market.market import Market
from pymongo import MongoClient
from collector.scheduler.base_scheduler import BaseScheduler
from optimizer.arbitrage_combination_optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


class IYOScheduler(BaseScheduler):
    interval_time_sec = 24 * 60 * 60

    def __init__(self, coin_name: str, mm1_abbr: str, mm2_abbr: str):
        self.coin_name = coin_name
        self.mm1_abbr = mm1_abbr
        self.mm2_abbr = mm2_abbr
        super().__init__()

    @BaseScheduler.interval_waiter(interval_time_sec)
    def _actual_run_in_loop(self):
        start_time = int(time.time()) - self.interval_time_sec
        end_time = int(time.time())

        Global.run_threaded(self.iyo_result_to_mongo_db,
                            [self.coin_name, self.mm1_abbr, self.mm2_abbr, start_time, end_time])

    @staticmethod
    def iyo_result_to_mongo_db(coin_name: str, mm1_abbr: str, mm2_abbr: str, start_time: int, end_time: int):

        Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db=True)
        db_client = MongoClient(mongodb_uri)

        # convert epoch time to local_time and log
        local_start_time = Global.convert_epoch_to_local_datetime(start_time, timezone="kr")
        local_end_time = Global.convert_epoch_to_local_datetime(end_time, timezone="kr")
        logging.warning("IYO conducting -> start_time: %s, end_time: %s" % (local_start_time, local_end_time))

        settings = {
            "target_currency": coin_name,
            "mm1": {
                "market_tag": getattr(Market, "VIRTUAL_%s" % mm1_abbr.upper()),
                "fee_rate": 0.001,
                "krw_balance": 1000000,
                "coin_balance": 10
            },
            "mm2": {
                "market_tag": getattr(Market, "VIRTUAL_%s" % mm2_abbr.upper()),
                "fee_rate": 0.00075,
                "krw_balance": 1000000,
                "coin_balance": 10

            },
            "division": 3,
            "depth": 5,
            "consecution_time": 30,
            "start_time": start_time,
            "end_time": end_time
        }

        bal_factor_settings = {
            "mm1": {
                "krw_balance": {"start": 0, "end": 20000000, "step_limit": 1000
                                },
                "coin_balance": {"start": 0, "end": 20, "step_limit": 0.1
                                 }
            },
            "mm2": {
                "krw_balance": {"start": 0, "end": 20000000, "step_limit": 1000
                                },
                "coin_balance": {"start": 0, "end": 20, "step_limit": 0.1
                                 }
            }
        }

        factor_settings = {
            "max_trading_coin": {"start": 0, "end": 0.8, "step_limit": 0.0001},
            "min_trading_coin": {"start": 0, "end": 0, "step_limit": 0},
            "new": {
                "threshold": {"start": 0, "end": 2500, "step_limit": 1},
                "factor": {"start": 1, "end": 1, "step_limit": 0.01}
            },
            "rev": {
                "threshold": {"start": 0, "end": 2500, "step_limit": 1},
                "factor": {"start": 1, "end": 1, "step_limit": 0.01}
            }
        }

        iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings)

        db_client["statistics"]["iyo"].insert_many(iyo_result)


if __name__ == "__main__":
    IYOScheduler("bch", "co", "gp").run()
