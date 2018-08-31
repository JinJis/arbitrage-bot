import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.initial_balance_optimizer import InitialBalanceOptimizer


def main(coin_name: str, mm1_name: str, mm2_name: str):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=False)
    start_time = Global.convert_local_datetime_to_epoch("2018.08.20 09:00:00", timezone="kr")
    end_time = Global.convert_local_datetime_to_epoch("2018.08.20 13:00:00", timezone="kr")

    iyo_config = Global.read_iyo_setting_config(coin_name)

    # set settings // fix manually if you need to
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

    ibo_result = InitialBalanceOptimizer.run(settings, bal_factor_settings)
    print(ibo_result)


if __name__ == '__main__':
    main("trx", "bithumb", "okcoin")
