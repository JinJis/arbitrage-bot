from trader.risk_free_arb_bot import RiskFreeArbBot2
import logging
import numpy as np
from analyzer.analyzer import Analyzer


class InitialSettingOptimizer:
    # 각각의 initial setting의 start, end, step 설정 받아오기
    def __init__(self, max_coin_start: float, max_coin_end: float, max_coin_step: float,
                 new_threshold_start: float, new_threshold_end: float, new_threshold_step: float,
                 rev_threshold_start: float, rev_threshold_end: float, rev_threshold_step: float,
                 rev_factor_start: float, rev_factor_end: float, rev_factor_step: float,
                 start_time, end_time):

        # max coin trading unit settings
        self.MAX_COIN_start = max_coin_start
        self.MAX_COIN_end = max_coin_end
        self.MAX_COIN_step = max_coin_step
        # NEW & REV threshold settings
        self.NEW_THRESHOLD_start = new_threshold_start
        self.NEW_THRESHOLD_end = new_threshold_end
        self.NEW_THRESHOLD_step = new_threshold_step
        self.REV_THRESHOLD_start = rev_threshold_start
        self.REV_THRESHOLD_end = rev_threshold_end
        self.REV_THRESHOLD_step = rev_threshold_step
        # REV factor settings
        self.REV_FACTOR_start = rev_factor_start
        self.REV_FACTOR_end = rev_factor_end
        self.REV_FACTOR_step = rev_factor_step

        # No need to be altered variables
        # FIXME: IF cosiderable amounts of money are invested, fix MIN_COIN_UNIT!
        self.MIN_COIN_UNIT = 0
        self.MAX_OB_INDEX = 1

        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        # Inject 'start, end, step' of each initial settings into lists
        max_coin_unit_list = np.arange(start=self.MAX_COIN_start, stop=self.MAX_COIN_end,
                                       step=self.MAX_COIN_step).tolist()
        min_coin_unit = self.MIN_COIN_UNIT
        max_ob_index = self.MAX_OB_INDEX
        new_th_list = np.arange(start=self.NEW_THRESHOLD_start, stop=self.NEW_THRESHOLD_end,
                                step=self.NEW_THRESHOLD_step).tolist()
        rev_th_list = np.arange(start=self.REV_THRESHOLD_start, stop=self.REV_THRESHOLD_end,
                                step=self.REV_THRESHOLD_step).tolist()
        rev_factor_list = np.arange(start=self.REV_FACTOR_start, stop=self.REV_FACTOR_end,
                                    step=self.REV_FACTOR_step).tolist()

        # Total Count
        total_counts = len(list(max_coin_unit_list)) * len(list(new_th_list)) * len(list(
            rev_th_list)) * len(list(rev_factor_list))
        logging.WARNING("Total Counts: %d" % total_counts)

        # Loop Through
        result = list()
        counter = 0
        for max_unit in max_coin_unit_list:
            for new_th in new_th_list:
                for rev_th in rev_th_list:
                    for rev_f in rev_factor_list:
                        bot = RiskFreeArbBot2(target_currency="bch", should_db_logging=False, is_backtesting=True,
                                              is_init_setting_opt=True,
                                              start_time=self.start_time, end_time=self.end_time)
                        bot.MAX_COIN_TRADING_UNIT = max_unit
                        bot.MIN_COIN_TRADING_UNIT = min_coin_unit
                        bot.MAX_OB_INDEX_NUM = max_ob_index
                        bot.NEW_SPREAD_THRESHOLD = new_th
                        bot.REV_SPREAD_THRESHOLD = rev_th
                        bot.REV_FACTOR = rev_f
                        bot.run()
                        krw_total_balance = bot.total_krw_bal
                        traded_new = bot.trade_new
                        traded_rev = bot.trade_rev
                        result.append([krw_total_balance, max_unit, new_th, rev_th, rev_f, traded_new, traded_rev])
                        logging.warning(
                            "[Progress] %d out of %d --- "
                            "[NEW #] %d, [REV #] %d ---"
                            " [MAX_UNI] %.4f, [NEW_TH] %d, [REV_TH] %d, [KRW Earned] %.2f " % (
                                counter + 1, total_counts, traded_new, traded_rev, max_unit, new_th, rev_th,
                                krw_total_balance))
                        counter += 1

        # Return Result
        opt_result_list = Analyzer.get_opt_initial_setting_list(result)
        logging.warning("==========================Finished!!==========================")

        opt_counter = 0
        for result in opt_result_list:
            opt_counter += 1
            logging.warning(
                "[OPT #%d] KRW_earned: %.4f, Max_Coin_Unit: %.5f, NEW_Threshold: %.3f, "
                "REV_Threshold: %.3f, REV_factor: %.2f, NEW #: %d, REV #: %d" % (
                    opt_counter, result[0], result[1], result[2], result[3], result[4], result[5], result[6]))
