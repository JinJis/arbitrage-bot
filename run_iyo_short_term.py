import logging
import itertools as it
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


def main(coin_name: str, start_time: str, end_time: str):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=True)
    db_client = SharedMongoClient.instance()

    logging.warning("Nohup conducting -> start_time: %s, end_time: %s" % (start_time, end_time))
    # Global.send_to_slack_channel("IYO Initiated!! start_time: %s, end_time: %s" % (prev_time, cur_time))

    start_time = Global.convert_local_datetime_to_epoch(start_time, timezone="kr")
    end_time = Global.convert_local_datetime_to_epoch(end_time, timezone="kr")

    # draw iyo_config for bal & factor_setting
    iyo_config = Global.read_iyo_setting_config(coin_name)

    rfab_combi_list = list(it.combinations(["gopax", "okcoin"], 2))
    for _combi in rfab_combi_list:
        logging.critical("[%s-%s-%s] IYO conducting -> start_time: %s, end_time: %s" % (
            coin_name.upper(), str(_combi[0]).upper(), str(_combi[1]).upper(), start_time, end_time))

        # set settings, bal_fact_settings, factor_settings
        settings = TradeSettingConfig.get_settings(mm1_name=_combi[0],
                                                   mm2_name=_combi[1],
                                                   target_currency=coin_name,
                                                   start_time=start_time, end_time=end_time,
                                                   division=iyo_config["division"],
                                                   depth=iyo_config["depth"],
                                                   consecution_time=iyo_config["consecution_time"],
                                                   is_virtual_mm=True)

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(iyo_config["krw_seq_end"])

        factor_settings = TradeSettingConfig.get_factor_settings(iyo_config["max_trade_coin_end"],
                                                                 iyo_config["threshold_end"],
                                                                 iyo_config["appx_unit_coin_price"])

        iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings)
        logging.critical("Final IYO result: %s" % iyo_result)


if __name__ == '__main__':

    # for short term (=< one day)
    # '2018.08.18 20:42:10', '2018.08.18 21:16:01'
    st_local = '2018.08.18 20:42:10'
    et_local = '2018.08.18 21:16:01'

    for target_currency in ["btc"]:
        main(target_currency, st_local, et_local)
    # Global.send_to_slack_channel("IYO for past date set done for all COMBINATION!! ")
