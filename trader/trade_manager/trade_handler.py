import time
import logging
from collector.oppty_time_collector import OpptyTimeCollector
from collector.scheduler.otc_scheduler import OTCScheduler
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from optimizer.base_optimizer import BaseOptimizer
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer
from trader.trade_manager.trade_stat_formula import TradeFormula, TradeFormulaApplied


class TradeHandler:
    INITIATION_REWEIND_TIME = 1 * 60 * 60
    TIME_DUR_TIL_SETTLEMENT = 4 * 60 * 60

    YIELD_THRESHOLD_RATE_START = 0.1
    YIELD_THRESHOLD_RATE_END = 0.7
    YIELD_THRESHOLD_RATE_STEP = 0.05

    FTI_FORMULA_WEIGHT_START = 0.1
    FTI_FORMULA_WEIGHT_END = 1.0
    FTI_FORMULA_WEIGHT_STEP = 0.01

    FTI_MIN_INTERVAL = 1

    MAX_TI_MULTIPLIER_START = 1
    MAX_TI_MULTIPLIER_END = 5
    MAX_TI_MULTIPLIER_STEP = 0.5

    def __init__(self, is_initiation_mode: bool, is_trading_mode: bool, streamer_settings: dict):

        self.is_initiation_mode = is_initiation_mode
        self.is_trading_mode = is_trading_mode

        self.mm1_name = streamer_settings["mm1_name"]
        self.mm2_name = streamer_settings["mm2_name"]
        self.mm1_krw_bal = streamer_settings["mm1_krw_bal"]
        self.mm2_krw_bal = streamer_settings["mm2_krw_bal"]
        self.mm1_coin_bal = streamer_settings["mm1_coin_bal"]
        self.mm2_coin_bal = streamer_settings["mm2_coin_bal"]
        self.target_currency = streamer_settings["target_currency"]

        self.bot_start_time = int(time.time())
        self.rewined_time = int(self.bot_start_time - self.INITIATION_REWEIND_TIME)

    def launch_inner_outer_ocat(self):
        # run Inner OCAT
        # decide which market has the most coin and make it as a set point
        if self.mm1_coin_bal > self.mm2_coin_bal:
            set_point_market = self.mm1_name
        elif self.mm1_coin_bal < self.mm2_coin_bal:
            set_point_market = self.mm2_name
        else:
            logging.info("Coin Balances for both are market same. Plz manually transfer coin")
            set_point_market = str(input("Manual coin transfer done, set_point_market is:"))
        self.run_inner_or_outer_ocat(set_point_market, self.target_currency, is_inner_ocat=True)

        # run Outer OCAT
        self.run_inner_or_outer_ocat(set_point_market, self.target_currency, is_inner_ocat=False)

    def to_proceed_handler_for_initiation_mode(self):

        to_proceed = str(input("Inner & Outer OCAT finished. Do you want to change any settings? (y/n)"))
        if to_proceed == "y":
            # set settings accordingly
            self.target_currency = str(input("Type target_currency:"))
            self.mm1_name = str(input("Type mm1_name:"))
            self.mm2_name = str(input("Type mm2_name:"))
            self.mm1_krw_bal = float(input("Type [%s]-[KRW] Balance:" % self.mm1_name.upper()))
            self.mm1_coin_bal = float(input("Type [%s]-[%s] Balance:"
                                            % (self.mm1_name.upper(), self.target_currency.upper())))
            self.mm2_krw_bal = float(input("Type [%s]-[KRW] Balance:" % self.mm2_name.upper()))
            self.mm2_coin_bal = float(input("Type [%s]-[%s] Balance:"
                                            % (self.mm2_name.upper(), self.target_currency.upper())))

            # change IYO config settings of krw, coin seq end
            Global.write_balance_seq_end_to_ini(krw_seq_end=self.mm1_krw_bal + self.mm2_krw_bal,
                                                coin_seq_end=self.mm1_coin_bal + self.mm2_coin_bal)
            return True

        if to_proceed == "n":
            logging.warning("Bot stopped")
            return False

        else:
            logging.warning("Irrelevant command. Please try again")
            return self.to_proceed_handler_for_initiation_mode()

    def run_inner_or_outer_ocat(self, set_point_market: str, target_currency: str, is_inner_ocat: bool):
        if is_inner_ocat:
            # create combination of coin that is injected by validating if the exchange has that coin
            logging.critical("Set Point Market is: [%s]" % set_point_market.upper())
            inner_ocat_list = Global.get_inner_ocat_combination(set_point_market, target_currency)
            logging.warning("--------Conducting Inner OCAT--------")
            ocat_final_result = self.otc_all_combination_by_one_coin(target_currency, inner_ocat_list)

        elif not is_inner_ocat:
            logging.warning("--------Conducting Outer OCAT--------")
            ocat_final_result = []
            for outer_ocat_coin in list(Global.read_avail_coin_in_list()):
                logging.warning("Now conducting [%s]" % outer_ocat_coin.upper())
                outer_ocat_list = Global.get_rfab_combination_list(outer_ocat_coin)
                ocat_result = self.otc_all_combination_by_one_coin(outer_ocat_coin, outer_ocat_list)
                ocat_final_result.extend(ocat_result)
        else:
            raise Exception("Please indicate if it is Inner OCAT or not")

        descending_order_result = OTCScheduler.sort_by_logest_oppty_time_to_lowest(ocat_final_result)
        top_ten_descend_order_result = descending_order_result[:10]

        for result in top_ten_descend_order_result:
            new_percent = (result["new"] / self.INITIATION_REWEIND_TIME) * 100
            rev_percent = (result["rev"] / self.INITIATION_REWEIND_TIME) * 100
            logging.warning("[%s] NEW: %.2f%%, REV: %.2f%%" % (result["combination"], new_percent, rev_percent))

    def otc_all_combination_by_one_coin(self, target_currency: str, combination_list: list):
        all_ocat_result_by_one_coin = []
        for _combi in combination_list:
            # draw iyo_config for settings
            iyo_config = Global.read_iyo_setting_config(target_currency)

            settings = TradeSettingConfig.get_settings(mm1_name=_combi[0],
                                                       mm2_name=_combi[1],
                                                       target_currency=target_currency,
                                                       start_time=self.rewined_time, end_time=self.bot_start_time,
                                                       division=iyo_config["division"],
                                                       depth=iyo_config["depth"],
                                                       consecution_time=iyo_config["consecution_time"],
                                                       is_virtual_mm=True)
            try:
                otc_result_dict = OpptyTimeCollector.run(settings=settings)
                total_dur_dict = OpptyTimeCollector.get_total_duration_time(otc_result_dict)
                total_dur_dict["combination"] = \
                    "%s-%s-%s" % (target_currency.upper(), str(_combi[0]).upper(), str(_combi[1]).upper())
                all_ocat_result_by_one_coin.append(total_dur_dict)
            except TypeError as e:
                logging.error("Something went wrong in OTC scheduler", e)
                continue

        return all_ocat_result_by_one_coin

    def run_monitoring_mode(self):
        # change time info up-to-date (since some minutes passed b/c of OCAT and Balance transfer
        self.bot_start_time = int(time.time())
        self.rewined_time = int(self.bot_start_time - self.INITIATION_REWEIND_TIME)

        if self.is_initiation_mode:
            logging.warning("Now conducting [Monitoring] for [Initiation Mode]")

            # launch Oppty Sliced IYO
            sliced_iyo_list = self.launch_oppty_sliced_iyo(self.bot_start_time, self.rewined_time)

            # get yield_histo_filtered dict
            yield_histo_filted_dict = TradeFormula.get_yield_histo_filtered_dict(sliced_iyo_list,
                                                                                 self.YIELD_THRESHOLD_RATE_START,
                                                                                 self.YIELD_THRESHOLD_RATE_END,
                                                                                 self.YIELD_THRESHOLD_RATE_STEP)

            # launch Formulated Trade Interval (FTI)
            fti_result = self.launch_formulated_trade_interval(yield_histo_filted_dict, self.rewined_time)
            logging.critical("FINAL FTI RESULT:\n %s" % fti_result)
            return fti_result

        if not self.is_initiation_mode:
            logging.warning("Now conducting [Monitoring] for [Monitoring Mode]")
            pass
        return

    def launch_formulated_trade_interval(self, yield_histo_filted_dict: dict, rewined_time: int):
        """
        :param yield_histo_filted_dict: {"0.1": [s-iyo, s-iyo..], "0.2": [....]}
        :param rewined_time: actual simulation start time (bot_start_time - time_anal_dur)
        :return: {"yield_threshold_rate":
                    {"fti_formula_weight":
                        "max_ti_multiplier"
                            "fti": [.....],
                            "fti_yield_list": [.....],
                            "fti_yield_sum": float,
                            "fti_exhaust_rate": float}}}
        """
        time_dur_til_settle = int(rewined_time + self.TIME_DUR_TIL_SETTLEMENT)
        result_dict = dict()
        for yield_th_rate in list(yield_histo_filted_dict.keys()):
            result_dict.update({yield_th_rate: {}})
            for fti_formul_weight in BaseOptimizer.generate_seq(self.FTI_FORMULA_WEIGHT_START,
                                                                self.FTI_FORMULA_WEIGHT_END,
                                                                self.FTI_FORMULA_WEIGHT_STEP):
                result_dict[yield_th_rate].update({fti_formul_weight: {}})
                for max_ti_multi in BaseOptimizer.generate_seq(self.MAX_TI_MULTIPLIER_START, self.MAX_TI_MULTIPLIER_END,
                                                               self.MAX_TI_MULTIPLIER_STEP):
                    fti_list, fti_yield_list, fti_exhaust_rate = \
                        TradeFormulaApplied.get_formulated_trade_interval(list(yield_histo_filted_dict[yield_th_rate]),
                                                                          self.mm1_krw_bal, self.mm2_krw_bal,
                                                                          time_dur_til_settle,
                                                                          fti_formul_weight, self.FTI_MIN_INTERVAL,
                                                                          max_ti_multi)
                    # add these infos to yield_histo_filted_dict by its key value
                    result_dict[yield_th_rate][fti_formul_weight].update({
                        max_ti_multi: {
                            "fti": fti_list,
                            "fti_yield_list": fti_yield_list,
                            "fti_yield_sum": sum(fti_yield_list),
                            "fti_exhaust_rate": fti_exhaust_rate
                        }})

        return result_dict

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

    @staticmethod
    def get_opt_fti_set_and_final_yield(fti_result: dict):
        # retrieve final optimized setting by calculating fti_yield * fti_exhaust rate
        opted_yield = None
        final_opted_fti_list = []
        for yield_th_rate in fti_result.keys():
            for fti_forml_weight in fti_result[yield_th_rate].keys():
                for max_ti_multi in fti_result[yield_th_rate][fti_forml_weight].keys():
                    target_dict = fti_result[yield_th_rate][fti_forml_weight][max_ti_multi]

                    try:
                        expted_settle_yield = target_dict["fti_yield_sum"] / target_dict["fti_exhaust_rate"]
                    except ZeroDivisionError:
                        continue

                    if opted_yield is None:
                        opted_yield = expted_settle_yield
                        continue
                    if expted_settle_yield > opted_yield:
                        opted_yield = expted_settle_yield
                        final_opted_fti_list.clear()
                        final_opted_fti_list.append(target_dict)
                    if expted_settle_yield == opted_yield:
                        final_opted_fti_list.append(target_dict)
        return final_opted_fti_list, opted_yield
