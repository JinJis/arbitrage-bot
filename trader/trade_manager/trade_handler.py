import time
import logging
from config.global_conf import Global
from config.config_market_manager import ConfigMarketManager
from optimizer.base_optimizer import BaseOptimizer
from config.trade_setting_config import TradeSettingConfig
from collector.scheduler.otc_scheduler import OTCScheduler
from collector.oppty_time_collector import OpptyTimeCollector
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer
from trader.market_manager.market_manager import MarketManager
from trader.trade_manager.trade_stat_formula import TradeFormulaApplied


class TradeHandler:
    INITIATION_REWEIND_TIME = 1 * 60 * 60
    TIME_DUR_OF_SETTLEMENT = 6 * 60 * 60

    # TODO 이쪽 활용해줘야함
    TRADING_REWIND_TIME = 5 * 60

    YIELD_THRESHOLD_RATE_START = 0.1
    YIELD_THRESHOLD_RATE_END = 0.5
    YIELD_THRESHOLD_RATE_STEP = 0.1

    FTI_FORMULA_WEIGHT_START = 0.1
    FTI_FORMULA_WEIGHT_END = 1.0
    FTI_FORMULA_WEIGHT_STEP = 0.05

    FTI_MIN_INTERVAL = 1

    MAX_TI_MULTIPLIER_START = 1
    MAX_TI_MULTIPLIER_END = 5
    MAX_TI_MULTIPLIER_STEP = 1

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager,
                 is_initiation_mode: bool, is_trading_mode: bool):

        self.is_initiation_mode = is_initiation_mode
        self.is_trading_mode = is_trading_mode

        self.mm1 = mm1
        self.mm2 = mm2
        self.mm1_name = mm1.get_market_name().lower()
        self.mm2_name = mm2.get_market_name().lower()
        self.mm1_krw_bal = float(mm1.balance.get_available_coin("krw"))
        self.mm2_krw_bal = float(mm2.balance.get_available_coin("krw"))
        self.mm1_coin_bal = float(mm1.balance.get_available_coin(target_currency))
        self.mm2_coin_bal = float(mm2.balance.get_available_coin(target_currency))
        self.target_currency = target_currency

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
            self.mm1: MarketManager = getattr(ConfigMarketManager, input("Type mm1!! ex) BITHUMB :")).value
            self.mm2: MarketManager = getattr(ConfigMarketManager, input("Type mm2!! ex) BITHUMB :")).value
            self.mm1_name = self.mm1.get_market_name().lower()
            self.mm2_name = self.mm2.get_market_name().lower()
            self.mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
            self.mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
            self.mm1_coin_bal = float(self.mm1.balance.get_available_coin(self.target_currency))
            self.mm2_coin_bal = float(self.mm2.balance.get_available_coin(self.target_currency))

            # change IYO config settings of krw, coin seq end
            Global.write_balance_seq_end_to_ini(krw_seq_end=self.mm1_krw_bal + self.mm2_krw_bal,
                                                coin_seq_end=self.mm1_coin_bal + self.mm2_coin_bal)
            return True

        if to_proceed == "n":
            logging.warning("Initiating with current settings!!")
            return True

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

    def launch_formulated_trade_interval(self, yield_histo_filted_dict: dict, rewined_time: int):
        time_of_settlement = int(rewined_time + self.TIME_DUR_OF_SETTLEMENT)

        fti_final_result_list = []
        for yield_th_rate in list(yield_histo_filted_dict.keys()):
            for fti_formul_weight in BaseOptimizer.generate_seq(self.FTI_FORMULA_WEIGHT_START,
                                                                self.FTI_FORMULA_WEIGHT_END,
                                                                self.FTI_FORMULA_WEIGHT_STEP):
                for max_ti_multi in BaseOptimizer.generate_seq(self.MAX_TI_MULTIPLIER_START, self.MAX_TI_MULTIPLIER_END,
                                                               self.MAX_TI_MULTIPLIER_STEP):
                    fti_iyos_result_dict = \
                        TradeFormulaApplied.get_formulated_trade_interval(list(yield_histo_filted_dict[yield_th_rate]),
                                                                          self.mm1_krw_bal, self.mm2_krw_bal,
                                                                          time_of_settlement,
                                                                          fti_formul_weight, self.FTI_MIN_INTERVAL,
                                                                          max_ti_multi)

                    # add these infos to yield_histo_filted_dict by its key value
                    fti_iyos_result_dict["yield_threshold_rate"] = yield_th_rate
                    fti_iyos_result_dict["fti_formula_weight"] = fti_formul_weight
                    fti_iyos_result_dict["max_time_interval_multiplier"] = max_ti_multi
                    fti_final_result_list.append(fti_iyos_result_dict)

        return fti_final_result_list

    @staticmethod
    def get_opt_fti_set_and_final_yield(fti_result: list):
        # retrieve final optimized setting by calculating fti_yield * fti_exhaust rate
        opted_yield = None
        final_opted_fti_iyo_list = []
        for fti_iyo_dict in fti_result:
            predicted_yield_by_settle = fti_iyo_dict["predicted_yield_by_settle"]

            if opted_yield is None:
                opted_yield = predicted_yield_by_settle
                final_opted_fti_iyo_list.append(fti_iyo_dict)
                continue
            if predicted_yield_by_settle > opted_yield:
                opted_yield = predicted_yield_by_settle
                final_opted_fti_iyo_list.clear()
                final_opted_fti_iyo_list.append(fti_iyo_dict)
            if predicted_yield_by_settle == opted_yield:
                final_opted_fti_iyo_list.append(fti_iyo_dict)

        return final_opted_fti_iyo_list

    @staticmethod
    def sort_final_opted_fti_iyo_list_by_min_avg_trade_interval(final_opted_fti_iyo_list: list):
        # if len(final_opted_fti_iyo_list) =! 1, then choose the best one
        if len(final_opted_fti_iyo_list) > 1:

            min_ti_sorted_fti_iyo_list = []
            min_trade_interval = None
            for fti_iyo_dict in final_opted_fti_iyo_list:

                # calc avg trade_interval of current iyo_dict
                avg_trade_interval = 0
                for iyo in fti_iyo_dict["fti_iyo_list"]:
                    avg_trade_interval += iyo["fti"]

                # sort by minimum
                if min_trade_interval is None:
                    min_trade_interval = avg_trade_interval
                    min_ti_sorted_fti_iyo_list.append(fti_iyo_dict)
                    continue
                if min_trade_interval > avg_trade_interval:
                    min_trade_interval = avg_trade_interval
                    min_ti_sorted_fti_iyo_list.clear()
                    min_ti_sorted_fti_iyo_list.append(fti_iyo_dict)
                if min_trade_interval == avg_trade_interval:
                    min_ti_sorted_fti_iyo_list.append(fti_iyo_dict)
                else:
                    continue
            return Global.find_middle_of_list(min_ti_sorted_fti_iyo_list)
        else:
            return final_opted_fti_iyo_list[0]

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