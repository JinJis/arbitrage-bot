import numpy as np


class TradeStatFormula:
    @staticmethod
    def get_area_percent_by_histo_formula(yield_list: list, yield_to_anal: float):
        # use this with the 5 sec (deafault) parsed IYO yield past data list
        histos, bin_edges = np.histogram(yield_list, density=True)
        area_percentage = 0
        for histo, edge in zip(histos, bin_edges):
            if edge > yield_to_anal:
                break
            area_percentage += histo * np.diff(bin_edges)[0]
        return area_percentage

    def yield_threshold_formula(self):
        pass

    def exhaustion_reamining_time_formula(self):
        pass
