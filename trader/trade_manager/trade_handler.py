import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from trader.trade_manager.trade_stat_formula import TradeFormulaApplied
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


class TradeHandler:

    @staticmethod
    def get_predicted_yield_list():
        # get yield_list
        # trading_interval_predicted
        # yield_list_expected
        pass

    @staticmethod
    def run_iyo_by_sliced_oppty(sliced_iyo_settings: dict):
        # draw iyo_config for bal & factor_setting
        iyo_config = Global.read_sliced_iyo_setting_config(sliced_iyo_settings["target_currency"])

        logging.critical("[%s-%s-%s] Sliced IYO conducting -> start_time: %s, end_time: %s" % (
            sliced_iyo_settings["target_currency"].upper(), sliced_iyo_settings["mm1_name"].upper(),
            sliced_iyo_settings["mm2_name"].upper(), sliced_iyo_settings["start_time"],
            sliced_iyo_settings["end_time"]))

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(iyo_config["krw_seq_end"],
                                                                       iyo_config["coin_seq_end"])

        factor_settings = TradeSettingConfig.get_factor_settings(iyo_config["max_trade_coin_end"],
                                                                 iyo_config["threshold_end"],
                                                                 iyo_config["appx_unit_coin_price"])

        sliced_iyo_result = IntegratedYieldOptimizer.run(sliced_iyo_settings, bal_factor_settings, factor_settings,
                                                         is_stat_appender=False, is_slicing_dur=True)

        try:
            TradeFormulaApplied.get_opt_trading_interval_from_sliced_iyo()
        return sliced_iyo_result
