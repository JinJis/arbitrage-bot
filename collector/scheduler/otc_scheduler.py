import time
import logging
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from config.trade_setting_config import TradeSettingConfig
from collector.scheduler.base_scheduler import BaseScheduler
from collector.oppty_time_collector import OpptyTimeCollector


class OTCScheduler(BaseScheduler):
    interval_time_sec = 60 * 30
    publishing_time = 210000  # ex) if 21:00:00 --> 210000

    def __init__(self):
        super().__init__()

    @BaseScheduler.interval_waiter(interval_time_sec)
    def _actual_run_in_loop(self):
        start_time = int(time.time()) - self.interval_time_sec
        end_time = int(time.time())

        # convert epoch time to local_time and log
        local_time = Global.convert_epoch_to_local_datetime(end_time, timezone="kr")

        local_time_conv = int(local_time[11:].replace(":", ""))
        if (local_time_conv > (self.publishing_time - self.interval_time_sec)) \
                and (local_time_conv < self.publishing_time + self.interval_time_sec):

            Global.run_threaded(self.oppty_time_publisher, ["bch", start_time, end_time])
            Global.run_threaded(self.oppty_time_publisher, ["btc", start_time, end_time])
            Global.run_threaded(self.oppty_time_publisher, ["eth", start_time, end_time])
            Global.run_threaded(self.oppty_time_publisher, ["qtum", start_time, end_time])
            Global.run_threaded(self.oppty_time_publisher, ["tron", start_time, end_time])
            Global.run_threaded(self.oppty_time_publisher, ["xrp", start_time, end_time])
        else:
            raise Exception("Publishing time not yet reached!!")

    @staticmethod
    def oppty_time_publisher(coin_name: str, start_time: int, end_time: int):
        Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
        SharedMongoClient.initialize(should_use_localhost_db=True)
        db_client = SharedMongoClient.instance()

        # create combination of coin that is injected by validating if the exchange has that coin
        rfab_combi_list = Global.get_rfab_combination_list(coin_name)

        final_otc_result_by_coin =
        for _combi in rfab_combi_list:
            logging.critical("[%s-%s-%s] OTC conducting -> start_time: %s, end_time: %s" % (
                coin_name.upper(), str(_combi[0]).upper(), str(_combi[1]).upper(), start_time, end_time))

            # draw iyo_config for settings
            iyo_config = Global.read_iyo_setting_config(coin_name)

            settings = TradeSettingConfig.get_settings(mm1=_combi[0],
                                                       mm2=_combi[1],
                                                       target_currency=coin_name,
                                                       start_time=start_time, end_time=end_time,
                                                       division=iyo_config["division"],
                                                       depth=iyo_config["depth"],
                                                       consecution_time=iyo_config["consecution_time"],
                                                       is_virtual_mm=True)

            otc_result_dict = OpptyTimeCollector.run(settings=settings)
            total_dur_dict = OpptyTimeCollector.get_total_duration_time(otc_result_dict)

            # save to excel


if __name__ == "__main__":
    IYOScheduler().run()
