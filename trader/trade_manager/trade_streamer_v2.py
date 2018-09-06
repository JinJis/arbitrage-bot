import time
import logging
from trader.trade_manager.trade_handler_v2 import TradeHandlerV2
from trader.market_manager.market_manager import MarketManager


class TradeStreamerV2(TradeHandlerV2):

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager):
        super().__init__(target_currency, mm1, mm2)

        # log when init
        logging.warning("================================")
        logging.warning("|| Trade Streamer Launched!!! ||")
        logging.warning("================================\n")
        logging.warning("[%s Balance] >> KRW: %f, %s: %f" % (self.mm1_name.upper(), self.mm1_krw_bal,
                                                             self.target_currency.upper(),
                                                             self.mm1_coin_bal))
        logging.warning("[%s Balance] >> KRW: %f, %s: %f\n" % (self.mm2_name.upper(), self.mm2_krw_bal,
                                                               self.target_currency.upper(),
                                                               self.mm2_coin_bal))

    def run(self):

        """ INITIATION MODE """
        try:
            if self.is_initiation_mode:

                # run initiation mode
                self.run_initiation_mode()

                # reset mode relevant
                self.is_initiation_mode = False
                self.is_trading_mode = True

                # self.launch_trading_mode()
        except KeyboardInterrupt:
            return

    # def launch_trading_mode(self):
    #     """ TRADING MODE """
    #     trading_loop_count = 0
    #     while True:
    #         if self.is_trading_mode:
    #
    #             # check if reached settlement time
    #             if self.trading_mode_start_time > self._settlement_time:
    #                 self.trade_handler_when_settlement_reached()
    #                 raise KeyboardInterrupt
    #
    #             # run trading_mode
    #             trading_loop_count += 1
    #             self.run_trading_mode(trading_loop_count)
    #
    #             # update balance
    #             self.update_balance()
    #
    #             # post rev_ledger to MongoDB
    #             self.post_updated_revenue_ledger()
    #
    #             # update bal seq by exhaust rate ctrl algorithm
    #             self.update_bal_seq_end_by_recent_bal_and_exhaust_ctrl()
    #
    #             # sleep by Trading Mode Loop Interval
    #             self.trading_mode_loop_sleep_handler(self.trading_mode_start_time, int(time.time()),
    #                                                  self.TRADING_MODE_LOOP_INTERVAL)
    #             # reset time relevant
    #             self.reset_time_relevant_for_trading_mode()
    #
    #         else:
    #             raise Exception("Trade Streamer should be launched with one of 3 modes -> "
    #                             "[INITIAL ANALYSIS MODE] / [TRADING MODE] / [OPPTY DETECTING MODE]")

    def run_initiation_mode(self):

        # run inner & outer OCAT
        self.launch_inner_outer_ocat()

        # check whether to proceed to next step
        self.to_proceed_handler_for_initiation_mode()

        logging.warning("================================")
        logging.warning("|| Conducting Initiation Mode ||")
        logging.warning("================================\n")

        # save spread_to_trade list & amount of krw_earend
        self.get_min_tradable_coin_unit_spread_list(self.initiation_rewind_time, self.streamer_start_time)

        # log spread_to_trade

    # def run_trading_mode(self, loop_count: int):
    #     logging.warning("======================================")
    #     logging.warning("|| Conducting Trading Mode -- # %4d ||" % loop_count)
    #     logging.warning("======================================\n")
    #
    #     final_opt_iyo_dict = self.run_fti_analysis()
    #
    #     # if there was no oppty, wait for oppty by looping real_time_streamer...
    #     if final_opt_iyo_dict is None:
    #         self.no_oppty_handler_for_trading_mode()
    #         return
    #
    #     # finally, post to MongoDB
    #     self.post_final_fti_result_to_mongodb(final_opt_iyo_dict)
    #
    #     # log final_opt_iyo_dict
    #     self.log_final_opt_result(final_opt_iyo_dict)
