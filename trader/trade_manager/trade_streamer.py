from collector.scheduler.base_scheduler import BaseScheduler
from trader.trade_manager.trade_stat_formula import TradeStatFormula
from config.global_conf import Global


class TradeStreamer:
    INITIATION_MODE_ANAL_DURATION = 3 * 60 * 60

    def __init__(self, is_initial_analysis_mode: bool, is_trading_mode: bool):
        self.is_initial_analysis_mode = is_initial_analysis_mode
        self.is_trading_mode = is_trading_mode

    def real_time_streamer(self):
        if self.is_initial_analysis_mode:
            self.run_initial_analysis_mode()
            self.is_initial_analysis_mode = False

        elif self.is_trading_mode:
            Global.run_threaded(self.run_monitoring_mode())
            Global.run_threaded(self.run_trading_mode())

        elif not self.is_trading_mode:
            self.run_monitoring_mode()
        else:
            raise Exception("Trade Streamer should be launched with one of 2 modes -> "
                            "[INITIAL ANALYSIS MODE] or [TRADING MODE]")

    def run_initial_analysis_mode(self):
        # collect best combination by OTC (input: which coin, which market that coin is deposited
        # for now, target_currency will not be transferred to the opt combination, so inject specific currency to trade

        # After making decision of target_combination, transfer krw accordingly
        # get init trade setting accordingly

        # get oppty_dur percentage
        # get yield avg, relative std --> set initial_yield_threshold

        # make popup window to show whether to proceed after krw transfered successfully, and proceed next step
        # after selecting proceed, run_trading_mode
        pass

    def run_monitoring_mode(self):
        # no trade but, tracking
        pass

    def run_trading_mode(self):
        pass
