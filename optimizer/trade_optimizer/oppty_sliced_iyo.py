from config.global_conf import Global
import logging
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer
from config.trade_setting_config import TradeSettingConfig


class OpptySlicedIYO:
    @staticmethod
    def run_iyo_by_sliced_oppty(coin_name: str, mm1_name: str, mm2_name: str, local_st: str, local_et):
        start_time = Global.convert_local_datetime_to_epoch(local_st, timezone="kr")
        end_time = Global.convert_local_datetime_to_epoch(local_et, timezone="kr")

        # draw iyo_config for bal & factor_setting
        sliced_iyo_config = Global.read_sliced_iyo_setting_config(coin_name)

        logging.critical("[%s-%s-%s] Sliced IYO conducting -> start_time: %s, end_time: %s" % (
            coin_name.upper(), mm1_name.upper(), mm2_name.upper(), start_time, end_time))

        # set settings, bal_fact_settings, factor_settings
        settings = TradeSettingConfig.get_settings(mm1_name=mm1_name,
                                                   mm2_name=mm2_name,
                                                   target_currency=coin_name,
                                                   start_time=start_time, end_time=end_time,
                                                   division=sliced_iyo_config["division"],
                                                   depth=sliced_iyo_config["depth"],
                                                   consecution_time=sliced_iyo_config["consecution_time"],
                                                   is_virtual_mm=True)

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(sliced_iyo_config["krw_seq_end"],
                                                                       sliced_iyo_config["coin_seq_end"])

        factor_settings = TradeSettingConfig.get_factor_settings(mm1_name, mm2_name, coin_name,
                                                                 sliced_iyo_config["max_trade_coin_end"],
                                                                 sliced_iyo_config["threshold_end"],
                                                                 sliced_iyo_config["appx_unit_coin_price"])

        sliced_iyo_list = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings,
                                                       is_stat_appender=False, is_slicing_dur=True)
        logging.critical("Final IYO result: %s" % sliced_iyo_list)
        return sliced_iyo_list, settings
