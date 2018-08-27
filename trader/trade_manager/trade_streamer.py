import time
import logging
from trader.trade_manager.trade_handler import TradeHandler
from trader.trade_manager.trade_stat_formula import TradeFormula
from trader.market_manager.market_manager import MarketManager


class TradeStreamer(TradeHandler):

    def __init__(self, mm1: MarketManager, mm2: MarketManager, target_currency: str):

        self.mm1 = mm1
        self.mm2 = mm2
        self.target_currency = target_currency
        self.is_initiation_mode = True
        self.is_trading_mode = False

        super().__init__(self.mm1, self.mm2, self.target_currency, self.is_initiation_mode, self.is_trading_mode)

    def real_time_streamer(self):
        if self.is_initiation_mode:
            logging.warning("==============================")
            logging.warning("|| Trade Streamer Initiated ||")
            logging.warning("==============================\n")
            logging.warning("[%s Balance] >> KRW: %f, %s: %f" % (self.mm1_name.upper(), self.mm1_krw_bal,
                                                                 self.target_currency.upper(),
                                                                 self.mm1_coin_bal))
            logging.warning("[%s Balance] >> KRW: %f, %s: %f\n" % (self.mm2_name.upper(), self.mm2_krw_bal,
                                                                   self.target_currency.upper(),
                                                                   self.mm2_coin_bal))
            final_opted_fti_dict = self.run_initiation_mode()

            # todo: post the result to MongoDB so that the Actual Trader can trigger them
            self.is_initiation_mode = False
            self.is_trading_mode = True

        elif self.is_trading_mode:
            # reset set_point_time
            self.bot_start_time = int(time.time())
            self.rewined_time = int(self.bot_start_time - self.TRADING_REWIND_TIME)
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
        # run inner & outer OCAT
        self.launch_inner_outer_ocat()

        # check whether to proceed to next step
        try:
            self.to_proceed_handler_for_initiation_mode()
        except False:
            return

        # run Monitoring mode (for initiation mode)
        self.bot_start_time = int(time.time())
        self.rewined_time = int(self.bot_start_time - self.INITIATION_REWEIND_TIME)
        fti_final_result_list = self.run_monitoring_mode()

        # loop through all fti_result and get the best one expected yield and its infos
        final_opted_fti_iyo_list = self.get_opt_fti_set_and_final_yield(fti_final_result_list)

        # finally get the best one set from fti_iyo_list
        final_opt_iyo_dict = self.sort_final_opted_fti_iyo_list_by_min_avg_trade_interval(final_opted_fti_iyo_list)

        return final_opt_iyo_dict

    def run_monitoring_mode(self):
        # change time info up-to-date (since some minutes passed b/c of OCAT and Balance transfer
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
            fti_final_result_list = self.launch_formulated_trade_interval(yield_histo_filted_dict, self.rewined_time)
            return fti_final_result_list

        if not self.is_initiation_mode:
            logging.warning("Now conducting [Monitoring] for [Monitoring Mode]")
            pass
        return
