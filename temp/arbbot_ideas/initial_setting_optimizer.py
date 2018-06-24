from analyzer.analyzer import ISOAnalyzer


class InitialSettingOptimizer:
    def __init__(self, trading_bot, initial_factor: dict, division: int, depth: int):
        self.MAX_COIN_TRADING_UNIT = None
        self.NEW_SPREAD_THRESHOLD = None
        self.REV_SPREAD_THRESHOLD = None
        self.NEW_FACTOR = None
        self.REV_FACTOR = None
        self.division = division
        self.depth = depth

        for factor in initial_factor.keys():
            value = initial_factor[factor]
            value["step"] = (value["end"] - value["start"]) / self.division
            setattr(self, factor, value)

        # initialize prerequisite attributes
        self.trading_bot = trading_bot
        self.initial_factor = initial_factor

    def run(self):
        # reduce as many cacluation odds as possible when operating for the first time
        # count NEW & REV oppty numbers
        self.trading_bot.run()
        new_oppty_num = self.trading_bot.new_oppty_counter
        rev_oppty_num = self.trading_bot.rev_oppty_counter
        print("Oppty Checked Successfully!! -- NEW oppty: %d, REV oppty: %d" % (new_oppty_num, rev_oppty_num))
        self.optimize_factor_with_new_rev_oppty(new_oppty_num, rev_oppty_num)

        # the main operation starts
        print("Now conducting optimization")
        return self.get_opt_factors_by_backtesting(self.depth)

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

    def get_opt_factors_by_backtesting(self, depth, optimized=None):
        if depth != 0:
            print("\n<<<< Now in depth: %d >>>>" % depth)
            # make all the RFAB2 attributes of initial setting
            for factor_name in self.initial_factor.keys():
                factor_dict = getattr(self, factor_name)
                start = factor_dict["start"]
                end = factor_dict["end"]
                step = factor_dict["step"]
                factor_dict["seq"] = ISOAnalyzer.start_end_step_to_list(start=start, end=end, step=step)
                print("%s: %s" % (factor_name, factor_dict["seq"]))
                if len(factor_dict["seq"]) == 0:
                    factor_dict["seq"] = [start]

            # now can loop through RFAB2 to get optimized result
            result = self.looper()
            current_optimized = ISOAnalyzer.get_opt_initial_setting_list(result)

            # adjust start, end, step according to the recent optimized intial setting values
            for index, factor_name in enumerate(self.initial_factor.keys()):
                i = index + 1
                factor = getattr(self, factor_name)
                cur_step = factor["step"]

                if factor["start"] < factor["end"]:
                    factor["start"] = current_optimized[i] - cur_step
                    if factor["start"] < 0:
                        factor["start"] = 0
                    factor["end"] = current_optimized[i] + cur_step
                    factor["step"] = (factor["end"] - factor["start"]) / self.division

            if optimized is None:
                optimized = current_optimized
            elif current_optimized[0] > optimized[0]:
                optimized = current_optimized
            print(optimized)

            depth -= 1
            return self.get_opt_factors_by_backtesting(depth, optimized)
        else:
            return optimized

    def looper(self):
        result = []
        total_odds = 1
        for factor_name in self.initial_factor.keys():
            total_odds *= len(getattr(self, factor_name)["seq"])

        counter = 1
        for new_f in self.NEW_FACTOR["seq"]:
            for rev_f in self.REV_FACTOR["seq"]:
                for rev_th in self.REV_SPREAD_THRESHOLD["seq"]:
                    for new_th in self.NEW_SPREAD_THRESHOLD["seq"]:
                        for max_unit in self.MAX_COIN_TRADING_UNIT["seq"]:
                            print("Now conducting %d out of %d" % (counter, total_odds))
                            setattr(self.trading_bot, "MAX_COIN_TRADING_UNIT", max_unit)
                            setattr(self.trading_bot, "NEW_SPREAD_THRESHOLD", new_th)
                            setattr(self.trading_bot, "REV_SPREAD_THRESHOLD", rev_th)
                            setattr(self.trading_bot, "NEW_FACTOR", new_f)
                            setattr(self.trading_bot, "REV_FACTOR", rev_f)
                            self.trading_bot.run()

                            krw_total_balance = self.trading_bot.total_krw_bal
                            semi_result = [krw_total_balance]
                            for factor_name in self.initial_factor.keys():
                                semi_result.append(getattr(self.trading_bot, factor_name))
                            semi_result.extend([self.trading_bot.trade_new, self.trading_bot.trade_rev])
                            result.append(semi_result)
                            counter += 1
        return result
