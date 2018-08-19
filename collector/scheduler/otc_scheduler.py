import time
import logging
from datetime import date, datetime
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from config.trade_setting_config import TradeSettingConfig
from collector.scheduler.base_scheduler import BaseScheduler
from collector.oppty_time_collector import OpptyTimeCollector


class OTCScheduler(BaseScheduler):
    interval_time_sec = 10
    time_dur_to_anal = 24 * 60 * 60
    publishing_time = "07:00:00"

    def __init__(self):
        Global.configure_default_root_logging(should_log_to_file=True, log_level=logging.CRITICAL)
        SharedMongoClient.initialize(should_use_localhost_db=True)
        super().__init__()

    @BaseScheduler.interval_waiter(interval_time_sec)
    def _actual_run_in_loop(self):
        now_date = int(time.time())

        convted_pub_time = datetime.strptime(self.publishing_time, "%H:%M:%S").time()
        publish_local_date = datetime.combine(date.today(), convted_pub_time).strftime("%Y.%m.%d %H:%M:%S %z")
        publish_epoch_date = Global.convert_local_datetime_to_epoch(str(publish_local_date), timezone="kr")

        start_time = publish_epoch_date - self.time_dur_to_anal
        end_time = publish_epoch_date

        if (now_date >= publish_epoch_date) \
                and (now_date <= publish_epoch_date + (self.interval_time_sec * 2)):
            logging.critical("OTC activated start_time: %d" % now_date)
            # loop through all possible coins and run
            final_result = []
            for target_currency in list(Global.read_avail_coin_in_list()):
                logging.critical("Now conducting %s" % target_currency.upper())
                result_by_one_coin = self.otc_all_mm_comb_by_one_coin(target_currency, start_time, end_time)
                final_result.extend(result_by_one_coin)

            # sort by highest to lowest oppty duration
            descending_order_result = self.sort_by_logest_oppty_time_to_lowest(final_result)

            # send this final result to slack in form of str
            start_local_date = Global.convert_epoch_to_local_datetime(start_time)
            self.send_result_nicely_to_slack(descending_order_result, start_local_date, publish_local_date)
        else:
            pass

    @staticmethod
    def otc_all_mm_comb_by_one_coin(coin_name: str, start_time: int, end_time: int) -> list:

        # create combination of coin that is injected by validating if the exchange has that coin
        rfab_combi_list = Global.get_rfab_combination_list(coin_name)

        all_comb_result_by_one_coin = []
        for _combi in rfab_combi_list:
            logging.critical("[%s-%s-%s] OTC conducting -> start_time: %s, end_time: %s" % (
                coin_name.upper(), str(_combi[0]).upper(), str(_combi[1]).upper(), start_time, end_time))

            # draw iyo_config for settings
            iyo_config = Global.read_iyo_setting_config(coin_name)

            settings = TradeSettingConfig.get_settings(mm1_name=_combi[0],
                                                       mm2_name=_combi[1],
                                                       target_currency=coin_name,
                                                       start_time=start_time, end_time=end_time,
                                                       division=iyo_config["division"],
                                                       depth=iyo_config["depth"],
                                                       consecution_time=iyo_config["consecution_time"],
                                                       is_virtual_mm=True)

            otc_result_dict = OpptyTimeCollector.run(settings=settings)
            total_dur_dict = OpptyTimeCollector.get_total_duration_time(otc_result_dict)
            total_dur_dict["combination"] = \
                "%s-%s-%s" % (coin_name.upper(), str(_combi[0]).upper(), str(_combi[1]).upper())
            all_comb_result_by_one_coin.append(total_dur_dict)
        return all_comb_result_by_one_coin

    @staticmethod
    def sort_by_logest_oppty_time_to_lowest(result: list):
        result.sort(key=lambda x: (x["new"] + x["rev"]), reverse=True)
        return result

    @classmethod
    def send_result_nicely_to_slack(cls, final_sorted_list: list, start_date: str, end_date: str):
        to_be_sent = str("[OTC start date: %s, end date: %s]\n" % (start_date, end_date))
        for result in final_sorted_list:
            new_percent = (result["new"] / cls.time_dur_to_anal) * 100
            rev_percent = (result["rev"] / cls.time_dur_to_anal) * 100
            to_be_sent += ("[%s]\n NEW: %.2f%%, REV: %.2f%%\n" % (result["combination"], new_percent, rev_percent))
        Global.send_to_slack_channel(to_be_sent)


if __name__ == "__main__":
    OTCScheduler().run()
