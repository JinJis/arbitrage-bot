from backtester.risk_free_arb_backtest import RfabBacktester


class InitialSettingOptimizer:
    def __init__(self, mm1_dict: dict, mm2_dict: dict, init_setting_dict: dict, initial_factor: dict, division: int,
                 depth: int):

        self.mm1_dict = mm1_dict
        self.mm2_dict = mm2_dict
        self.init_setting_dict = init_setting_dict
        self.division = division
        self.depth = depth

        for factor in initial_factor.keys():
            value = initial_factor[factor]
            value["step"] = ((value["end"] - value["start"]) / self.division)
            setattr(self, factor, value)

        self.initial_factor = initial_factor

    def run(self):
        # reduce as many cacluation odds as possible when operating for the first time
        # count NEW & REV oppty numbers
        self.trading_bot.run()
        new_oppty_num = self.trading_bot.new_oppty_counter
        rev_oppty_num = self.trading_bot.rev_oppty_counter
        print("Oppty Checked Successfully!! -- NEW oppty: %d, REV oppty: %d" % (new_oppty_num, rev_oppty_num))
        self.optimize_factor_with_new_rev_oppty(new_oppty_num, rev_oppty_num)

    def optimize_factor_with_new_rev_oppty(self, new_oppty_num, rev_oppty_num):
        # classify the kind of strategies and renew factor_settings accordingly
        if rev_oppty_num == 0:
            # by doing this, un-iterable REV related lists get created
            self.REV_SPREAD_THRESHOLD["end"] = self.REV_SPREAD_THRESHOLD["start"]
            self.REV_FACTOR["end"] = self.REV_FACTOR["start"]
            self.NEW_FACTOR["end"] = self.NEW_FACTOR["start"]
            return
        if new_oppty_num == 0:
            # by doing this, un-iterable NEW related lists get created
            self.NEW_SPREAD_THRESHOLD["end"] = self.NEW_SPREAD_THRESHOLD["start"]
            self.NEW_FACTOR["end"] = self.NEW_FACTOR["start"]
            self.REV_FACTOR["end"] = self.REV_FACTOR["start"]
            return
        if new_oppty_num > rev_oppty_num:
            self.NEW_FACTOR["end"] = self.NEW_FACTOR["start"]
        elif new_oppty_num < rev_oppty_num:
            self.REV_FACTOR["end"] = self.REV_FACTOR["start"]
        else:
            self.NEW_FACTOR["end"] = self.NEW_FACTOR["start"]
            self.REV_FACTOR["end"] = self.REV_FACTOR["start"]
