import time
import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from trader.trade_manager.trade_handler import TradeHandler
from trader.trade_manager.trade_stat_formula import TradeFormula
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer
from optimizer.base_optimizer import BaseOptimizer


class TradeStreamer:
    INITIATION_REWEIND_TIME = 3 * 60 * 60
    SLCING_INTERVAL = 120
    YIELD_RANK_PERCENT_START = 0.1
    YIELD_RANK_PERCENT_END = 0.5
    YIELD_RANK_PERCENT_STEP = 0.1

    def __init__(self, is_initiation_mode: bool, is_trading_mode: bool, settings: dict):
        self.is_initiation_mode = is_initiation_mode
        self.is_trading_mode = is_trading_mode
        self.target_currency = settings["target_currency"]
        self.mm1_name = settings["mm1_name"]
        self.mm2_name = settings["mm2_name"]

    def real_time_streamer(self):
        if self.is_initiation_mode:
            self.run_initiation_mode()
            self.is_initiation_mode = False

        elif self.is_trading_mode:
            Global.run_threaded(self.run_monitoring_mode())
            Global.run_threaded(self.run_trading_mode())

        elif not self.is_trading_mode:
            self.run_monitoring_mode()
        else:
            raise Exception("Trade Streamer should be launched with one of 2 modes -> "
                            "[INITIAL ANALYSIS MODE] or [TRADING MODE]")

    def run_initiation_mode(self, running_time: int):
        start_time = int(time.time())
        rewined_time = start_time - self.INITIATION_REWEIND_TIME

        # run Optimized Combination for Actual Trader (OCAT)
        pass

        # run Monitoring mode (for initiation mode)
        self.run_monitoring_mode(start_time, rewined_time, self.SLCING_INTERVAL)

        bot_started_time = int(time.time())
        roll_back_time_for_anal = int(time.time() - anal_dur)
        exp_anal_stop_time = roll_back_time_for_anal + running_time
        sliced_iyo_settings = Global.read_sliced_iyo_setting_config(self.target_currency)
        sliced_iyo_result_list = TradeHandler.run_iyo_by_sliced_oppty()

        pass

    def run_monitoring_mode(self, start_time: int, rewinded_time: int, slicing_interval: int, ):
        if self.is_initiation_mode:
            logging.warning("Now conducting [Monitoring] for [Initiation Mode]")

            # launch Oppty Sliced IYO
            sliced_iyo_list = self.launch_oppty_sliced_iyo(start_time, rewinded_time, slicing_interval)

            # get yield_histo_filtered dict
            yield_histo_filted_dict = self.get_yield_histo_filtered_dict(sliced_iyo_list)

        if not self.is_initiation_mode:
            logging.warning("Now conducting [Monitoring] for [Monitoring Mode]")
            pass
        return

    def run_trading_mode(self):
        pass

    # Fixme: 이 부분 TradeStatFormula나 IYO쪽으로 뽑기
    def launch_oppty_sliced_iyo(self, start_time: int, rewinded_time: int, slicing_interval: int):
        logging.critical("[%s-%s-%s] Sliced IYO conducting -> start_time: %s, rewinded_time: %s" % (
            self.target_currency.upper(), self.mm1_name.upper(), self.mm2_name.upper(), start_time, rewinded_time))

        # draw iyo_config for bal & factor_setting
        sliced_iyo_config = Global.read_sliced_iyo_setting_config(self.target_currency)
        # set settings, bal_fact_settings, factor_settings
        settings = TradeSettingConfig.get_settings(mm1_name=self.mm1_name,
                                                   mm2_name=self.mm2_name,
                                                   target_currency=self.target_currency,
                                                   start_time=start_time, end_time=rewinded_time,
                                                   division=sliced_iyo_config["division"],
                                                   depth=sliced_iyo_config["depth"],
                                                   consecution_time=sliced_iyo_config["consecution_time"],
                                                   is_virtual_mm=True)

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(sliced_iyo_config["krw_seq_end"],
                                                                       sliced_iyo_config["coin_seq_end"])

        factor_settings = TradeSettingConfig.get_factor_settings(sliced_iyo_config["max_trade_coin_end"],
                                                                 sliced_iyo_config["threshold_end"],
                                                                 sliced_iyo_config["appx_unit_coin_price"])

        return IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings,
                                            is_stat_appender=False, is_slicing_dur=True,
                                            slicing_interval=slicing_interval)

    # Fixme: 이 부분 TradeStatFormula 쪽으로 뽑아내기
    def get_yield_histo_filtered_dict(self, sliced_iyo_list: list):
        """
        :param sliced_iyo_list: [s_iyo, s_iyo, s_iyo....]
        :return:
        yield_rank_filtered_dict =
        {"0.1": [filtered_iyo, filt_iyo, ....],
         "0.2": [filtered_iyo, filt_iyo, ....],
         ...
        }
        """
        # calculate rank_perent for each s_iyo data and append to original
        s_iyo_yield_list = [x["yield"] for x in sliced_iyo_list]
        for s_iyo in sliced_iyo_list:
            yield_rank_percent = TradeFormula.get_area_percent_by_histo_formula(s_iyo_yield_list, s_iyo["yield"])
            s_iyo["yield_rank_percent"] = yield_rank_percent

        # create yield rank sequence to loop and analyze further down
        yield_rank_filtered_dict = dict()
        for rank_percent in BaseOptimizer.generate_seq(self.YIELD_RANK_PERCENT_START, self.YIELD_RANK_PERCENT_END,
                                                       self.YIELD_RANK_PERCENT_STEP):

            yield_histo_filtered_list = []
            for s_iyo in sliced_iyo_list:
                if s_iyo["yield_rank_percent"] >= rank_percent:
                    yield_histo_filtered_list.append(s_iyo)
                else:
                    continue
            yield_rank_filtered_dict[rank_percent] = yield_histo_filtered_list

        return yield_rank_filtered_dict
