import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


def main(coin_name: str, mm1_name: str, mm2_name: str, start_time: str, end_time: str, slicing_interval: int):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=False)

    logging.warning("Nohup conducting -> start_time: %s, end_time: %s" % (start_time, end_time))
    # Global.send_to_slack_channel("IYO Initiated!! start_time: %s, end_time: %s" % (prev_time, cur_time))

    start_time = Global.convert_local_datetime_to_epoch(start_time, timezone="kr")
    end_time = Global.convert_local_datetime_to_epoch(end_time, timezone="kr")

    # draw iyo_config for bal & factor_setting
    iyo_config = Global.read_sliced_iyo_setting_config(coin_name)

    logging.critical("[%s-%s-%s] IYO conducting -> start_time: %s, end_time: %s" % (
        coin_name.upper(), mm1_name.upper(), mm2_name.upper(), start_time, end_time))

    # set settings, bal_fact_settings, factor_settings
    settings = TradeSettingConfig.get_settings(mm1_name=mm1_name,
                                               mm2_name=mm2_name,
                                               target_currency=coin_name,
                                               start_time=start_time, end_time=end_time,
                                               division=iyo_config["division"],
                                               depth=iyo_config["depth"],
                                               consecution_time=iyo_config["consecution_time"],
                                               is_virtual_mm=True)

    bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(iyo_config["krw_seq_end"],
                                                                   iyo_config["coin_seq_end"])

    factor_settings = TradeSettingConfig.get_factor_settings(iyo_config["max_trade_coin_end"],
                                                             iyo_config["threshold_end"],
                                                             iyo_config["appx_unit_coin_price"])

    iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings,
                                              is_stat_appender=False, is_slicing_dur=True,
                                              slicing_interval=slicing_interval)
    logging.critical("Final IYO result: %s" % iyo_result)
    return iyo_result


if __name__ == '__main__':
    # for short term (=< one day)
    st_local = "2018.08.25 22:00:00"
    et_local = "2018.08.26 01:00:00"

    parsed_iyo_result = main("btc", "gopax", "okcoin", st_local, et_local, slicing_interval=120)

    yield_result = []
    for iyo in parsed_iyo_result:
        yield_result.append(iyo["yield"])

    print(yield_result)
