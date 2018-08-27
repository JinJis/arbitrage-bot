import numpy as np
from optimizer.base_optimizer import BaseOptimizer


class TradeFormulaApplied:

    @staticmethod
    def get_formulated_trade_interval(sliced_iyo_list: list, mm1_krw_bal: float, mm2_krw_bal: float,
                                      settlement_time: int, weight: float, min_trade_interval: int,
                                      max_trade_interval_multiplier: int):
        """
        :return:
        fti_iyos_result_dict = {
            "fti_exhaust_rate": flaot,
            "fti_iyo_list": [iyo, iyo, iyo...]
                            ** iyo = {
                                "fti",
                                "fti_yield"
                            }
        }
        """
        target_formula = TradeFormula.formulated_trading_interval_formula

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

        # loop through sliced_iyo_list and apply real_time simulation
        # plz remember that FTI is an abbreviation of Formulated Trade Interval

        fti_iyos_result_dict = dict()
        temp_iyo_list = []
        for iyo in sliced_iyo_list:

            # calc need params for Predicted Trading Interval FOURMULA
            # iyo는 무조건 100% exhaust --> actual exhaust rate 으로 변환
            act_exhaust_rate = iyo["total_krw_exhausted"] / cur_end_krw_bal
            remain_time_sec = settlement_time - iyo["settings"]["start_time"]

            # calc iyo_run_time
            iyo_run_time = (iyo["settings"]["end_time"] - iyo["settings"]["start_time"])
            # if iyo_run_time is 0, skip b/c it triggers target formula Zerodevision error
            if iyo_run_time == 0:
                continue

            # get trade ratio (traded new + rev / new + rev oppty count)
            trade_ratio = (iyo["new_traded"] + iyo["rev_traded"]) / (iyo["new_oppty_count"] + iyo["rev_oppty_count"])

            # calc trading_interval by formulated equation; Predicted Trading Interval Formula.
            # in order to opt the formula by multiplying weight
            calced_trade_interval = int(weight * target_formula(trade_ratio, act_exhaust_rate,
                                                                remain_time_sec, iyo_run_time))

            # if calculated trading_interval is between trading time and min_trade_interval -> good to go
            if min_trade_interval <= calced_trade_interval <= iyo_run_time:
                pass
            # if calced_trading_interval is less than min_trade_interval -> min_trade_interval
            if calced_trade_interval < min_trade_interval:
                calced_trade_interval = min_trade_interval
            # if calced_trading_interval is greater than iyo_run_time -> iyo_run_time
            if iyo_run_time < calced_trade_interval < max_trade_interval_multiplier * iyo_run_time:
                calced_trade_interval = iyo_run_time
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
            expted_yield = iyo["yield"] * (5 / calced_trade_interval) * (cur_end_krw_bal / iyo["total_krw_exhausted"])

            # finally append them to the original s-IYO dictionary
            iyo["fti"] = calced_trade_interval
            iyo["fti_yield"] = expted_yield
            temp_iyo_list.append(iyo)

        # after looping all the s-iyos, calculate PTIed KRW exhaust rate for further analysis for actual trader
        fti_iyos_result_dict["fti_exhaust_rate"] = (initial_krw_bal - cur_end_krw_bal) / initial_krw_bal
        fti_iyos_result_dict["fti_iyo_list"] = temp_iyo_list

        return fti_iyos_result_dict


class TradeFormula:
    @staticmethod
    def formulated_trading_interval_formula(trade_ratio: float, actual_exhaust_rate: float,
                                            remain_time_sec: int, iyo_run_time: int):
        return (actual_exhaust_rate * remain_time_sec * 5 * trade_ratio) / iyo_run_time  # 5는 iyo 기본 trade interval

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

    @staticmethod
    def get_yield_histo_filtered_dict(sliced_iyo_list: list,
                                      yield_th_rate_start, yield_th_rate_end, yield_th_rate_step):
        """
        :param sliced_iyo_list: [s_iyo, s_iyo, s_iyo....]
        :param yield_th_rate_start
        :param yield_th_rate_end
        :param yield_th_rate_step
        :return:
        yield_rank_filtered_dict =
        {"0.1": [filtered_iyo, filt_iyo, ....],
         "0.2": [filtered_iyo, filt_iyo, ....],
         ...
        }
        """
        # calculate rank_perent for each s_iyo data and append to original
        s_iyo_yield_list = [x["yield"] for x in sliced_iyo_list]
        for s_iyo in sliced_iyo_list:
            yield_threshold_rate = TradeFormula.get_area_percent_by_histo_formula(s_iyo_yield_list, s_iyo["yield"])
            s_iyo["yield_threshold_rate"] = yield_threshold_rate

        # create yield rank sequence to loop and analyze further down
        yield_rank_filtered_dict = dict()
        for yield_th_rate in BaseOptimizer.generate_seq(yield_th_rate_start, yield_th_rate_end,
                                                        yield_th_rate_step):

            yield_histo_filtered_list = []
            for s_iyo in sliced_iyo_list:
                if s_iyo["yield_threshold_rate"] >= yield_th_rate:
                    yield_histo_filtered_list.append(s_iyo)
                else:
                    continue
            yield_rank_filtered_dict[yield_th_rate] = yield_histo_filtered_list

        return yield_rank_filtered_dict
