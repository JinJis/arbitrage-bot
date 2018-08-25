import time
import logging
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from trader.trade_manager.trade_stat_formula import TradeFormula, TradeFormulaApplied
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer
from optimizer.base_optimizer import BaseOptimizer


class TradeStreamer:
    INITIATION_REWEIND_TIME = 3 * 60 * 60

    YIELD_THRESHOLD_RATE_START = 0.1
    YIELD_THRESHOLD_RATE_END = 0.7
    YIELD_THRESHOLD_RATE_STEP = 0.1

    FTI_FORMULA_WEIGHT_START = 0.1
    FTI_FORMULA_WEIGHT_END = 1.0
    FTI_FORMULA_WEIGHT_STEP = 0.1

    FTI_REWIND_TIME = 3 * 60 * 60
    FTI_MIN_INTERVAL = 1

    def __init__(self, is_initiation_mode: bool, is_trading_mode: bool, streamer_settings: dict):
        self.is_initiation_mode = is_initiation_mode
        self.is_trading_mode = is_trading_mode
        self.mm1_name = streamer_settings["mm1_name"]
        self.mm2_name = streamer_settings["mm2_name"]
        self.mm1_krw_bal = streamer_settings["mm1_krw_bal"]
        self.mm2_krw_bal = streamer_settings["mm2_krw_bal"]
        self.target_currency = streamer_settings["target_currency"]

        self.bot_start_time = int(time.time())

    def real_time_streamer(self):
        if self.is_initiation_mode:
            self.run_initiation_mode()
            self.is_initiation_mode = False

        elif self.is_trading_mode:
            # Global.run_threaded(self.run_monitoring_mode())
            # Global.run_threaded(self.run_trading_mode())
            pass

        elif not self.is_trading_mode:
            # self.run_monitoring_mode()
            pass
        else:
            raise Exception("Trade Streamer should be launched with one of 2 modes -> "
                            "[INITIAL ANALYSIS MODE] or [TRADING MODE]")

    def run_initiation_mode(self):
        rewined_time = self.bot_start_time - self.INITIATION_REWEIND_TIME

        # run Optimized Combination for Actual Trader (OCAT)

        # run Monitoring mode (for initiation mode)
        self.run_monitoring_mode(self.bot_start_time, rewined_time)

        # roll_back_time_for_anal = self.bot_start_time - )
        # exp_anal_stop_time = roll_back_time_for_anal + running_time
        # sliced_iyo_settings = Global.read_sliced_iyo_setting_config(self.target_currency)
        # sliced_iyo_result_list = TradeHandler.run_iyo_by_sliced_oppty()

        pass

    def run_monitoring_mode(self, anal_start_time: int, rewinded_time: int):
        if self.is_initiation_mode:
            logging.warning("Now conducting [Monitoring] for [Initiation Mode]")

            # launch Oppty Sliced IYO
            sliced_iyo_list = self.launch_oppty_sliced_iyo(anal_start_time, rewinded_time)

            # get yield_histo_filtered dict
            yield_histo_filted_dict = self.get_yield_histo_filtered_dict(sliced_iyo_list)

            # launch Formulated Trade Interval (FTI)
            fti_result = self.launch_formulated_trade_interval(yield_histo_filted_dict)

            return fti_result

        if not self.is_initiation_mode:
            logging.warning("Now conducting [Monitoring] for [Monitoring Mode]")
            pass
        return

    def run_trading_mode(self):
        pass

    def launch_formulated_trade_interval(self, yield_histo_filted_dict: dict):

        fti_result_dict = dict()
        for yield_th_rate in list(yield_histo_filted_dict.keys()):
            for fti_formul_weight in BaseOptimizer.generate_seq(self.FTI_FORMULA_WEIGHT_START,
                                                                self.FTI_FORMULA_WEIGHT_END,
                                                                self.FTI_FORMULA_WEIGHT_STEP):
                fti_list, fti_yield_list, fti_exhaust_rate = \
                    TradeFormulaApplied.get_formulated_trade_interval(list(yield_histo_filted_dict[yield_th_rate]),
                                                                      self.mm1_krw_bal, self.mm2_krw_bal,
                                                                      self.bot_start_time,
                                                                      fti_formul_weight, self.FTI_MIN_INTERVAL)
                # add these infos to yield_histo_filted_dict by its key value
                fti_result_dict.update({yield_th_rate: {
                    "fti": fti_list,
                    "fti_yield": fti_yield_list,
                    "fti_exhaust_rate": fti_exhaust_rate
                }})

        return fti_result_dict

    # Fixme: 이 부분 TradeStatFormula나 IYO쪽으로 뽑기
    def launch_oppty_sliced_iyo(self, anal_start_time: int, rewinded_time: int):
        logging.critical("[%s-%s-%s] Sliced IYO conducting -> start_time: %s, rewinded_time: %s" % (
            self.target_currency.upper(), self.mm1_name.upper(), self.mm2_name.upper(), anal_start_time, rewinded_time))

        # draw iyo_config for bal & factor_setting
        sliced_iyo_config = Global.read_sliced_iyo_setting_config(self.target_currency)
        # set settings, bal_fact_settings, factor_settings
        settings = TradeSettingConfig.get_settings(mm1_name=self.mm1_name,
                                                   mm2_name=self.mm2_name,
                                                   target_currency=self.target_currency,
                                                   start_time=rewinded_time, end_time=anal_start_time,
                                                   division=sliced_iyo_config["division"],
                                                   depth=sliced_iyo_config["depth"],
                                                   consecution_time=sliced_iyo_config["consecution_time"],
                                                   is_virtual_mm=True)

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(sliced_iyo_config["krw_seq_end"],
                                                                       sliced_iyo_config["coin_seq_end"])

        factor_settings = TradeSettingConfig.get_factor_settings(sliced_iyo_config["max_trade_coin_end"],
                                                                 sliced_iyo_config["threshold_end"],
                                                                 sliced_iyo_config["appx_unit_coin_price"])

        slicied_iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings,
                                                          is_stat_appender=False, is_slicing_dur=True,
                                                          slicing_interval=sliced_iyo_config["slicing_interval"])
        return slicied_iyo_result

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
        for rank_percent in BaseOptimizer.generate_seq(self.YIELD_THRESHOLD_RATE_START, self.YIELD_THRESHOLD_RATE_END,
                                                       self.YIELD_THRESHOLD_RATE_STEP):

            yield_histo_filtered_list = []
            for s_iyo in sliced_iyo_list:
                if s_iyo["yield_rank_percent"] >= rank_percent:
                    yield_histo_filtered_list.append(s_iyo)
                else:
                    continue
            yield_rank_filtered_dict[rank_percent] = yield_histo_filtered_list

        return yield_rank_filtered_dict
