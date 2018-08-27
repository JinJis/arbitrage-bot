import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from config.shared_mongo_client import SharedMongoClient
from collector.oppty_time_collector import OpptyTimeCollector


def main(coin_name: str, mm1_name: str, mm2_name: str, start_time_local: str, end_time_local: str):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.WARNING)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    start_time = Global.convert_local_datetime_to_epoch(start_time_local, timezone="kr")
    end_time = Global.convert_local_datetime_to_epoch(end_time_local, timezone="kr")

    iyo_config = Global.read_iyo_setting_config(coin_name)

    settings = TradeSettingConfig.get_settings(mm1_name=mm1_name,
                                               mm2_name=mm2_name,
                                               target_currency=coin_name,
                                               start_time=start_time, end_time=end_time,
                                               division=iyo_config["division"],
                                               depth=iyo_config["depth"],
                                               consecution_time=iyo_config["consecution_time"],
                                               is_virtual_mm=True)

    OpptyTimeCollector.run(settings)


if __name__ == '__main__':
    st_local = "2018.08.25 22:30:10"
    et_local = "2018.08.26 01:28:10"
    main("btc", "gopax", "okcoin", st_local, et_local)
