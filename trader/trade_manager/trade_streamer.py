import time
import logging
from trader.trade_manager.trade_handler import TradeHandler
from trader.market_manager.market_manager import MarketManager


class TradeStreamer(TradeHandler):

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager):
        super().__init__(target_currency, mm1, mm2, is_initiation_mode=True, is_trading_mode=False)

    def real_time_streamer(self):

        while True:

            """ INITIATION MODE """
            if self.is_initiation_mode:

                # first, make Actual Trader not to trade before Analysis
                self.post_empty_fti_setting_to_mongo_when_no_oppty()

                # run initiation mode
                self.run_initiation_mode()

                # reset mode relevant
                self.is_initiation_mode = False
                self.is_trading_mode = True

                # reset time relevant
                self.reset_time_relevant_before_trading_mode()

            """ TRADING MODE """
            if self.is_trading_mode:

                # check if reached settlement time
                if self.trading_mode_start_time > self.settlement_time:
                    self.trade_handler_when_settlement_reached()
                    return False

                # run trading_mode
                try:
                    self.run_trading_mode()
                # if no oppty
                except AssertionError:
                    self.no_oppty_handler_for_trading_mode()
                    return self.real_time_streamer()

                # sleep by Trading Mode Loop Interval
                self.trading_mode_loop_sleep_handler(self.trading_mode_start_time, int(time.time()),
                                                     self.TRADING_MODE_LOOP_INTERVAL)

                # reset time relevant
                self.reset_time_relevant_for_trading_mode()

            else:
                raise Exception("Trade Streamer should be launched with one of 3 modes -> "
                                "[INITIAL ANALYSIS MODE] / [TRADING MODE] / [OPPTY DETECTING MODE]")

    def run_initiation_mode(self):
        # log initiation mode
        logging.error("================================")
        logging.error("|| Trade Streamer Launched!!! ||")
        logging.error("================================\n")
        logging.error("[%s Balance] >> KRW: %f, %s: %f" % (self.mm1_name.upper(), self.mm1_krw_bal,
                                                           self.target_currency.upper(),
                                                           self.mm1_coin_bal))
        logging.warning("[%s Balance] >> KRW: %f, %s: %f\n" % (self.mm2_name.upper(), self.mm2_krw_bal,
                                                               self.target_currency.upper(),
                                                               self.mm2_coin_bal))
        # run inner & outer OCAT
        self.launch_inner_outer_ocat()

        # check whether to proceed to next step
        try:
            self.to_proceed_handler_for_initiation_mode()
        except False:
            return

        logging.error("================================")
        logging.error("|| Conducting Initiation Mode ||")
        logging.error("================================\n")

        self.initiation_start_time = int(time.time())
        self.init_rewined_time = int(self.initiation_start_time - self.INITIATION_REWEIND_TIME)

        # run FTI Analysis mode (for initiation mode)
        final_opt_iyo_dict = self.run_fti_analysis()

        # if there was no oppty, stop bot
        if final_opt_iyo_dict is None:
            self.is_initiation_mode = False
            self.is_trading_mode = False
            return

        # log initiation mode oppty_dur during
        self.log_final_opt_result(final_opt_iyo_dict)

        # finally, post to MongoDB
        self.post_final_fti_result_to_mongodb(final_opt_iyo_dict)

    def run_trading_mode(self):
        logging.error("=============================")
        logging.error("|| Conducting Trading Mode ||")
        logging.error("=============================\n")

        final_opt_iyo_dict = self.run_fti_analysis()

        # if there was no oppty, wait for oppty by looping real_time_streamer...
        if final_opt_iyo_dict is None:
            raise AssertionError

        # finally, post to MongoDB
        self.post_final_fti_result_to_mongodb(final_opt_iyo_dict)

        # log oppty duration during trading mode anal dur
        self.log_oppty_dur_of_trading_mode_fti_anal()

        # log final_opt_iyo_dict
        self.log_final_opt_result(final_opt_iyo_dict)
