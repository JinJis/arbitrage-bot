import logging
import time

from config.global_conf import Global
from trader.market_manager.market_manager import MarketManager
from trader.trade_streamer.trade_handler_v2 import TradeHandlerV2


class TradeStreamerV2(TradeHandlerV2):

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager, is_test: bool):

        super().__init__(target_currency, mm1, mm2, is_test)

        # update for the first time
        self.post_empty_trade_commander()
        self.post_empty_bal_commander()

        # check backup

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
        self.launch_initiation_mode()
        self.trading_mode_looper()
        return

    def launch_initiation_mode(self):
        # set initial trade settings
        self.set_initial_trade_setting()

        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logging.warning("||| Conducting Initiation Mode |||")
        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

        # # save spread_to_trade list & amount of krw_earend
        self.get_past_mtcu_spread_info_init_mode(self.ocat_rewind_time, self.streamer_start_time)

        # log MCTU info and decide spread threshold
        self.log_init_mode_mtcu_info()

        # init balance ledger
        self.update_and_post_all_ledgers(mode_status="initiation")

        # init excel ledger
        self.launch_balance_ledger_xlsx(mode_status="initiation")

        # update time relevant
        self.set_time_relevant_before_trading_mode()

    def trading_mode_looper(self):

        trading_loop_count = 0
        while True:

            # check if reached settlement time
            if self.trading_mode_now_time > self._settlement_time:
                self.settlement_handler()
                break

            try:
                # update balance & time
                self.update_balance(mode_status="trading")
                self.update_and_post_all_ledgers(mode_status="trading")
                self.trading_mode_now_time = int(time.time())

                # run trading_mode
                trading_loop_count += 1

                self.run_trading_mode_analysis(trading_loop_count)

                # post trade_commander dict to MongoDB
                self.post_trade_commander_to_mongo()

                # log rev ledger info
                self.log_balance_ledger()

                # sleep by Trading Mode Loop Interval
                self.trading_mode_loop_sleep_handler(self.trading_mode_now_time, int(time.time()),
                                                     self.TRADING_MODE_LOOP_INTERVAL)
            except Exception as e:
                log = "Error occured while executing Trade Streamer - Trading mode..\n" + str(e)
                logging.error(log)
                Global.send_to_slack_channel(Global.SLACK_STREAM_STATUS_URL, log)

    def run_trading_mode_analysis(self, loop_count: int):

        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logging.warning("|| Conducting Trading Mode -- # %4d || " % loop_count)
        logging.warning("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

        # get latest mm1, mm2 orderbook
        self.get_latest_orderbook()

        # get MTCU
        self.update_trade_condition_by_mtcu_analyzer()

        # log MCTU
        self.log_trading_mode_mtcu_info(self.streamer_start_time, self.trading_mode_now_time)

        # trade command by comparing current flowed time with exhaustion rate
        self.renew_exhaust_condition_by_time_flow()
