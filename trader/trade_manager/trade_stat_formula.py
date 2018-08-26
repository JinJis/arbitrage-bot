import numpy as np


class TradeFormulaApplied:

    @staticmethod
    def get_formulated_trade_interval(sliced_iyo_list: list, mm1_krw_bal: float, mm2_krw_bal: float,
                                      settlement_time: int, weight: float, min_trade_interval: int,
                                      max_trade_interval_multiplier: int):
        target_formula = TradeFormula.formulated_trading_interval_formula

        # plz remember that FTI is an abbreviation of Formulated Trade Interval
        fti_list = []

        # decide whether each IYO data was NEW or REV
        new_traded_count = 0
        rev_traded_count = 0
        for iyo in sliced_iyo_list:
            new_traded_count += iyo["new_traded"]
            rev_traded_count += iyo["rev_traded"]

        # set initial krw balance by attained result of NEW or REV
        if new_traded_count > rev_traded_count:
            cur_end_krw_bal = mm1_krw_bal
        else:
            cur_end_krw_bal = mm2_krw_bal

        initial_krw_bal = cur_end_krw_bal
        if initial_krw_bal == 0:
            print("yes")

        # loop through sliced_iyo_list and apply real_time simulation
        fti_yield_list = []

        for iyo in sliced_iyo_list:

            # calc need params for Predicted Trading Interval FOURMULA
            act_exhaust_rate = iyo["exhaust_rate"] * (iyo["total_krw_invested"] / cur_end_krw_bal)
            remain_time_sec = settlement_time - iyo["settings"]["start_time"]

            # skip if start & end time is equal --> inexplicable data that triggers Formula Zerodevision

            # calc iyo_run_time
            iyo_run_time = (iyo["settings"]["end_time"] - iyo["settings"]["start_time"])
            # if iyo_run_time is 0, skip b/c it triggers target formula Zerodevision error
            if iyo_run_time == 0:
                continue

            # calc trading_interval by formulated equation; Predicted Trading Interval Formula.
            # in order to opt the formula by multiplying weight
            calced_trade_interval = int(weight * target_formula(act_exhaust_rate, remain_time_sec, iyo_run_time))

            # if calculated trading_interval is between trading time and min_trade_interval -> good to go
            if min_trade_interval <= calced_trade_interval <= iyo_run_time:
                fti_list.append(calced_trade_interval)
            # if calced_trading_interval is less than min_trade_interval -> min_trade_interval
            if calced_trade_interval < min_trade_interval:
                calced_trade_interval = min_trade_interval
                fti_list.append(calced_trade_interval)
            # if calced_trading_interval is greater than iyo_run_time -> iyo_run_time
            if iyo_run_time < calced_trade_interval < max_trade_interval_multiplier * iyo_run_time:
                calced_trade_interval = iyo_run_time
                fti_list.append(calced_trade_interval)
            else:
                continue

            # subtract actual traded krw applied with calced_trading_interval from current krw balance
            krw_traded = cur_end_krw_bal * act_exhaust_rate * (5 / calced_trade_interval)

            # if current_krw_bal is fully exhausted, stop current iyo_data
            if cur_end_krw_bal - krw_traded <= 0:
                continue

            # if current_krw_bal is still holdable, trade
            cur_end_krw_bal -= krw_traded

            # append yield updated with trading_interval_time and subtacted krw real_time balance
            # FIXME: 과연 여기가 줄어든 KRW를 반영한 수익률인가? --> 애초에 yield 구했던거 다시 점검 필요!!!
            expted_yield = iyo["yield"] * (5 / calced_trade_interval) * (cur_end_krw_bal / iyo["total_krw_invested"])
            fti_yield_list.append(round(expted_yield, 10))

        # finally, calculate PTIed KRW exhaust rate for further analysis for actual trader
        fti_exhaust_rate = (initial_krw_bal - cur_end_krw_bal) / initial_krw_bal

        return fti_list, fti_yield_list, fti_exhaust_rate

    def exhaustion_reamining_time_formula(self):
        pass


class TradeFormula:
    @staticmethod
    def formulated_trading_interval_formula(actual_exhaust_rate: float, remain_time_sec: int, iyo_run_time: int):
        return (actual_exhaust_rate * remain_time_sec * 5) / iyo_run_time  # 5는 iyo 기본 trade interval

    @staticmethod
    def get_area_percent_by_histo_formula(past_data_list: list, current_data: float):
        # use this with the 5 sec (deafault) parsed IYO yield past data list
        histos, bin_edges = np.histogram(past_data_list, density=True)
        area_percentage = 0
        for histo, edge in zip(histos, bin_edges):
            if edge > current_data:
                break
            area_percentage += histo * np.diff(bin_edges)[0]
        return area_percentage
