import numpy as np
from optimizer.base_optimizer import BaseOptimizer


class TradeFormulaApplied:

    @staticmethod
    def get_formulated_trade_interval(sliced_iyo_list: list, mm1_krw_bal: float, mm2_krw_bal: float,
                                      settlement_time: int, weight: float, min_trade_interval: int,
                                      max_trade_interval_multiplier: int):

        target_formula = TradeFormula.formulated_trading_interval_formula

        cur_end_krw_bal = mm1_krw_bal + mm2_krw_bal

        initial_krw_bal = cur_end_krw_bal

        # loop through sliced_iyo_list and apply real_time simulation
        # plz remember that FTI is an abbreviation of Formulated Trade Interval

        fti_iyos_result_dict = dict()
        temp_iyo_list = []
        total_krw_earned = 0
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
            if trade_ratio == 0:
                continue

            # calc trading_interval by formulated equation; Predicted Trading Interval Formula.
            # in order to opt the formula by multiplying weight
            calced_trade_interval = int(weight * target_formula(trade_ratio, act_exhaust_rate,
                                                                remain_time_sec, iyo_run_time))

            # if calculated trading_interval is between trading time and min_trade_interval -> good to go
            if min_trade_interval <= calced_trade_interval <= iyo_run_time:
                pass
            # if calced_trading_interval is less than min_trade_interval -> min_trade_interval
            elif calced_trade_interval < min_trade_interval:
                calced_trade_interval = min_trade_interval
            # if calced_trading_interval is greater than iyo_run_time -> iyo_run_time
            elif iyo_run_time < calced_trade_interval < max_trade_interval_multiplier * iyo_run_time:
                calced_trade_interval = calced_trade_interval
            elif max_trade_interval_multiplier * iyo_run_time < calced_trade_interval:
                continue

            # calc actual krw_traded and krw_earned
            krw_traded = iyo["total_krw_exhausted"] * (5 / (trade_ratio * calced_trade_interval))
            krw_earned = iyo["krw_earned"] * (5 / (trade_ratio * calced_trade_interval))

            # if current_krw_bal is fully exhausted, stop current iyo_data
            if cur_end_krw_bal - krw_traded <= 0:
                continue

            # append yield updated with trading_interval_time and subtacted krw real_time balance
            expted_yield = krw_earned / cur_end_krw_bal * 100
            total_krw_earned += krw_earned

            # if current_krw_bal is still holdable, trade
            cur_end_krw_bal -= krw_traded

            # finally append them to the original s-IYO dictionary
            iyo["fti"] = calced_trade_interval
            iyo["fti_yield"] = expted_yield
            temp_iyo_list.append(iyo)

        # after looping all the s-iyos, calculate PTIed KRW exhaust rate for further analysis for actual trader
        fti_iyos_result_dict["fti_exhaust_rate"] = (initial_krw_bal - cur_end_krw_bal) / initial_krw_bal
        fti_iyos_result_dict["fti_yield_sum"] = total_krw_earned / initial_krw_bal * 100

        # there may be some situations where no krw_earned, because of weights and multiplier..so handle
        if fti_iyos_result_dict["fti_yield_sum"] == 0:
            fti_iyos_result_dict["predicted_yield_by_settle"] = 0
        else:
            fti_iyos_result_dict["predicted_yield_by_settle"] \
                = (total_krw_earned / fti_iyos_result_dict["fti_exhaust_rate"]) / initial_krw_bal * 100
        fti_iyos_result_dict["fti_iyo_list"] = temp_iyo_list

        return fti_iyos_result_dict

    @staticmethod
    def extract_yield_dict_from_s_iyo_list(sliced_iyo_list: list):
        # make yield dict in list
        s_iyo_yield_dict_list = [{"yield": x["yield"],
                                  "start_time": x["settings"]["start_time"],
                                  "end_time": x["settings"]["end_time"]} for x in sliced_iyo_list]
        return s_iyo_yield_dict_list

    @staticmethod
    def get_yield_histo_filtered_dict(past_s_iyo_list: list,
                                      yield_th_rate_start, yield_th_rate_end, yield_th_rate_step):

        # extract yield from past data and make it a list
        yield_only_list = [x["yield"] for x in past_s_iyo_list]

        # calc yield rank rate
        for s_iyo in past_s_iyo_list:
            yield_rank_rate = TradeFormula.get_area_percent_by_histo_formula(yield_only_list, s_iyo["yield"])
            s_iyo["yield_rank_rate"] = yield_rank_rate

        # create yield rank sequence to loop and analyze further down
        yield_rank_filtered_dict = dict()
        for yield_th_rate in BaseOptimizer.generate_seq(yield_th_rate_start, yield_th_rate_end,
                                                        yield_th_rate_step):

            yield_histo_filtered_list = []
            for s_iyo in past_s_iyo_list:
                if s_iyo["yield_rank_rate"] >= yield_th_rate:
                    yield_histo_filtered_list.append(s_iyo)
                else:
                    continue
            yield_rank_filtered_dict[yield_th_rate] = yield_histo_filtered_list

        return yield_rank_filtered_dict


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
