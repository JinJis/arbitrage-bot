import time
import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from config.trade_setting_config import TradeSettingConfig
from collector.scheduler.base_scheduler import BaseScheduler
from optimizer.arbitrage_combination_optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


class IYOScheduler(BaseScheduler):
    interval_time_sec = 24 * 60 * 60

    def __init__(self):
        super().__init__()

    @BaseScheduler.interval_waiter(interval_time_sec)
    def _actual_run_in_loop(self):
        start_time = int(time.time()) - self.interval_time_sec
        end_time = int(time.time())

        Global.run_threaded(self.iyo_result_to_mongo_db, ["bch", start_time, end_time])
        Global.run_threaded(self.iyo_result_to_mongo_db, ["btc", start_time, end_time])
        Global.run_threaded(self.iyo_result_to_mongo_db, ["eth", start_time, end_time])
        Global.run_threaded(self.iyo_result_to_mongo_db, ["qtum", start_time, end_time])
        Global.run_threaded(self.iyo_result_to_mongo_db, ["tron", start_time, end_time])
        Global.run_threaded(self.iyo_result_to_mongo_db, ["xrp", start_time, end_time])

    @staticmethod
    def iyo_result_to_mongo_db(coin_name: str, start_time: int, end_time: int):
        Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
        SharedMongoClient.initialize(should_use_localhost_db=True)
        db_client = SharedMongoClient.instance()

        # convert epoch time to local_time and log
        local_st = Global.convert_epoch_to_local_datetime(start_time, timezone="kr")
        local_et = Global.convert_epoch_to_local_datetime(end_time, timezone="kr")

        # create combination of coin that is injected by validating if the exchange has that coin
        rfab_combi_list = Global.get_rfab_combination_list(coin_name)

        for _combi in rfab_combi_list:
            logging.critical("[%s-%s-%s] IYO conducting -> start_time: %s, end_time: %s" % (
                coin_name.upper(), str(_combi[0]).upper(), str(_combi[1]).upper(), local_st, local_et))

            # draw iyo_config for bal & factor_setting
            iyo_config = Global.read_iyo_setting_config(coin_name)

            settings = TradeSettingConfig.get_settings(mm1=_combi[0],
                                                       mm2=_combi[1],
                                                       target_currency=coin_name,
                                                       start_time=start_time, end_time=end_time,
                                                       division=iyo_config["division"],
                                                       depth=iyo_config["depth"],
                                                       consecution_time=iyo_config["consecution_time"],
                                                       is_virtual_mm=True)

            bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(iyo_config["krw_seq_end"])

            factor_settings = TradeSettingConfig.get_factor_settings(iyo_config["max_trade_coin_end"],
                                                                     iyo_config["threshold_end"],
                                                                     iyo_config["factor_end"],
                                                                     iyo_config["appx_unit_coin_price"])

            iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings)

            # finally save to mongoDB
            db_client["statistics"]["iyo"].insert_many(iyo_result)


if __name__ == "__main__":
    IYOScheduler().run()
