import time
import logging
from config.global_conf import Global
from trader.trade_manager.trade_handler_v2 import TradeHandlerV2
from trader.market_manager.market_manager import MarketManager


class TradeStreamerV2(TradeHandlerV2):

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager):

        super().__init__(target_currency, mm1, mm2)

        # update for the first time
        self.post_empty_trade_commander()

        # log when init
        logging.warning("================================")
        logging.warning("|| Trade Streamer Launched!!! || ")
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

                # set initial trade settings
                self.set_initial_trade_setting()

                # run initiation mode
                self.run_initiation_mode_analysis()

                # init revenue ledger
                self.update_revenue_ledger(mode_status="initiation")

                # update time relevant
                self.set_time_relevant_before_trading_mode()

                # reset mode relevant
                self.is_initiation_mode = False
                self.is_trading_mode = True

                # launch trading mode
                self.trading_mode_looper()

                # if reached settlement
                if self.settlment_reached:
                    self.settlement_handler()

        except Exception as e:
            log = "CRITICAL Error occured while executing Trade Streamer.. Not a type occured in Trading Mode.." \
                  "Stopping Streamer..!!\n" + str(e)
            logging.error(log)
            Global.send_to_slack_channel(Global.SLACK_STREAM_STATUS_URL, log)
            raise KeyboardInterrupt

    def trading_mode_looper(self):
        """ TRADING MODE """
        trading_loop_count = 0
        while True:

            # check if reached settlement time
            if self.trading_mode_now_time > self._settlement_time:
                self.settlment_reached = True
                return

            # update balance & time
            self.update_balance()
            self.update_revenue_ledger(mode_status="trading")
            self.trading_mode_now_time = int(time.time())

            # run trading_mode
            trading_loop_count += 1
            try:
                self.run_trading_mode_analysis(trading_loop_count)
            except Exception as e:
                log = "Error occured while executing Trade Streamer - Trading mode..\n" + str(e)
                logging.error(log)
                Global.send_to_slack_channel(Global.SLACK_STREAM_STATUS_URL, log)

            # post trade_commander dict to MongoDB
            self.post_trade_commander_to_mongo()

            # log rev ledger info
            self.log_rev_ledger()

            # sleep by Trading Mode Loop Interval
            self.trading_mode_loop_sleep_handler(self.trading_mode_now_time, int(time.time()),
                                                 self.TRADING_MODE_LOOP_INTERVAL)

    def run_initiation_mode_analysis(self):

        # run inner & outer OCAT
        # fixme: 필요하다면 사용!
        # self.launch_inner_outer_ocat()

        # check whether to proceed to next step
        self.to_proceed_handler_for_initiation_mode()

        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logging.warning("||| Conducting Initiation Mode |||")
        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

        # # save spread_to_trade list & amount of krw_earend
        self.get_min_tradable_coin_unit_spread_list_init_mode(self.ocat_rewind_time, self.streamer_start_time)

        # log MCTU info and decide spread threshold
        self.log_past_mctu_info()

        self.mctu_spread_threshold = float(input("Decide MCTU spread threshold: "))
        self.mctu_royal_spread = float(input("Decide MCTU Royal spread: "))

    def run_trading_mode_analysis(self, loop_count: int):

        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logging.warning("|| Conducting Trading Mode -- # %4d || " % loop_count)
        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

        # get MTCU
        self.get_min_tradable_coin_unit_spread_list_trading_mode()

        # log MCTU
        self.log_present_mctu_info(self.streamer_start_time, self.trading_mode_now_time)

        # trade command by comparing current flowed time with exhaustion rate
        self.trade_command_by_comparing_exhaustion_with_flow_time()
