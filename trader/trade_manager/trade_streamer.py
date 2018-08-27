import logging
from trader.trade_manager.trade_handler import TradeHandler


class TradeStreamer(TradeHandler):

    def __init__(self, is_initiation_mode: bool, is_trading_mode: bool, streamer_settings: dict):
        super().__init__(is_initiation_mode, is_trading_mode, streamer_settings)

    def real_time_streamer(self):
        if self.is_initiation_mode:
            final_opted_fti_set, opted_yield = self.run_initiation_mode()
            logging.critical("Final Opted FTI set\n%s" % final_opted_fti_set)
            logging.critical("Final Opted Yield\n%s" % opted_yield)
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
        # run inner & outer OCAT
        self.launch_inner_outer_ocat()

        # check whether to proceed to next step
        try:
            self.to_proceed_handler_for_initiation_mode()
        except False:
            return

        # run Monitoring mode (for initiation mode)
        fti_result = self.run_monitoring_mode()

        # loop through all fti_result and get the best expected yield and its infos
        final_opted_fti_set_list, opted_yield = self.get_opt_fti_set_and_final_yield(fti_result)

        return final_opted_fti_set_list, opted_yield
