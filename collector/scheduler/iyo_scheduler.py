import time
import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from pymongo import MongoClient
from collector.scheduler.base_scheduler import BaseScheduler
from optimizer.arbitrage_combination_optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


class IYOScheduler(BaseScheduler):
    interval_time_sec = 24 * 60 * 60

    def __init__(self, coin_name: str, mm1_name: str, mm2_name: str):
        """
        :param coin_name: ex) bch, btc, xrp...
        :param mm1_name: ex) coinone, korbit, bithumb...
        :param mm2_name: ex) coinone, korbit, bithumb...
        """
        self.coin_name = coin_name
        self.mm1_name = mm1_name
        self.mm2_name = mm2_name
        super().__init__()

    @BaseScheduler.interval_waiter(interval_time_sec)
    def _actual_run_in_loop(self):
        start_time = int(time.time()) - self.interval_time_sec
        end_time = int(time.time())

        Global.run_threaded(self.iyo_result_to_mongo_db,
                            [self.coin_name, self.mm1_name, self.mm2_name, start_time, end_time])

    @staticmethod
    def iyo_result_to_mongo_db(coin_name: str, mm1_name: str, mm2_name: str, start_time: int, end_time: int):
        Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db=True)
        db_client = MongoClient(mongodb_uri)

        # convert epoch time to local_time and log
        local_start_time = Global.convert_epoch_to_local_datetime(start_time, timezone="kr")
        local_end_time = Global.convert_epoch_to_local_datetime(end_time, timezone="kr")
        logging.warning("IYO conducting -> start_time: %s, end_time: %s" % (local_start_time, local_end_time))

        settings = TradeSettingConfig.get_settings(mm1=mm1_name, mm2=mm2_name,
                                                   target_currency=coin_name,
                                                   start_time=start_time, end_time=end_time,
                                                   is_virtual_mm=True)

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings()
        factor_settings = TradeSettingConfig.get_factor_settings()

        iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings)

        db_client["statistics"]["iyo"].insert_many(iyo_result)


if __name__ == "__main__":
    IYOScheduler("bch", "co", "gp").run()
