import logging
from config.global_conf import Global
from config.trade_setting_config import MarketSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.arbitrage_combination_optimizer.initial_balance_optimizer import InitialBalanceOptimizer

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=True)
start_time = Global.convert_local_datetime_to_epoch("2018.07.11 09:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.07.11 13:00:00", timezone="kr")

# set settings // fix manually if you need to
settings = MarketSettingConfig.get_settings(mm1="coinone",
                                            mm2="gopax",
                                            target_currency="bch",
                                            start_time=start_time, end_time=end_time,
                                            is_virtual_mm=True)

bal_factor_settings = MarketSettingConfig.get_bal_fact_settings(krw_seq_end=10000000)

IBO_result = InitialBalanceOptimizer.run(settings, bal_factor_settings)
print(IBO_result)
