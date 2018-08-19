import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.initial_setting_optimizer import InitialSettingOptimizer

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=False)
start_time = Global.convert_local_datetime_to_epoch("2018.07.11 09:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.07.11 14:00:00", timezone="kr")

settings = TradeSettingConfig.get_settings(mm1_name="coinone",
                                           mm2_name="gopax",
                                           target_currency="bch",
                                           start_time=start_time, end_time=end_time,
                                           is_virtual_mm=True)

factor_settings = TradeSettingConfig.get_factor_settings(max_trade_coin_end=0.1,
                                                         threshold_end=2500,
                                                         appx_unit_coin_price=800000)

ISO_result = InitialSettingOptimizer().run(settings, factor_settings)
print(ISO_result)
