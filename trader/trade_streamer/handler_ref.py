from analyzer.trade_analyzer import BasicAnalyzer


class Recorder:
    def __init__(self):
        self.rev_ledger = None
        self.spread_dict = {
            "init": dict(new=[], rev=[]),
            "trade": dict(new=[], rev=[])
        }


class Threshold:
    def __init__(self):
        self.NEW = {
            "normal": None,
            "royal": None
        }
        self.REV = {
            "normal": None,
            "royal": None
        }


class Condition:
    def __init__(self):
        self.is_settlement = False
        self.NEW = {
            "is_time_flow_above_exhaust": None,
            "is_oppty": False,
            "is_royal": False
        }
        self.REV = {
            "is_time_flow_above_exhaust": None,
            "is_oppty": False,
            "is_royal": False
        }

    @staticmethod
    def trade_execution_decider(cond_dict: dict):
        if cond_dict["is_time_flow_above_exhaust"] and cond_dict["is_oppty"]:
            execute_trade = True
        else:
            if cond_dict["is_royal"]:
                execute_trade = True
            else:
                execute_trade = False
        return execute_trade


class Exhaustion:
    @staticmethod
    def rate_to_dict(mm1_ob: dict, mm2_ob: dict, rev_ledger: dict):

        # get mid price
        mm1_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(mm1_ob)
        mm2_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(mm2_ob)
        mid_price = (mm1_mid_price + mm2_mid_price) / 2

        # calc remaining currency bal to exhaust further
        new_krw_to_exhaust = rev_ledger["current_bal"]["krw"]["mm1"]
        new_coin_to_exhaust = rev_ledger["current_bal"]["coin"]["mm2"] * mid_price
        rev_krw_to_exhaust = rev_ledger["current_bal"]["krw"]["mm2"]
        rev_coin_to_exhaust = rev_ledger["current_bal"]["coin"]["mm1"] * mid_price

        # NEW exhaust
        # if krw bal is larger than coin converted to krw by real exchange rate,
        if new_krw_to_exhaust >= new_coin_to_exhaust:
            new_init_bal = rev_ledger["initial_bal"]["coin"]["mm2"]
            new_cur_bal = rev_ledger["current_bal"]["coin"]["mm2"]
        else:
            new_init_bal = rev_ledger["initial_bal"]["krw"]["mm1"]
            new_cur_bal = rev_ledger["current_bal"]["krw"]["mm1"]

        # REV exhaust
        # if krw bal is larger than coin converted to krw by real exchange rate,
        if rev_krw_to_exhaust >= rev_coin_to_exhaust:
            rev_init_bal = rev_ledger["initial_bal"]["coin"]["mm1"]
            rev_cur_bal = rev_ledger["current_bal"]["coin"]["mm1"]
        else:
            rev_init_bal = rev_ledger["initial_bal"]["krw"]["mm2"]
            rev_cur_bal = rev_ledger["current_bal"]["krw"]["mm2"]

        # in case cur bal > init bal (in case of inflow of new investment)
        if new_cur_bal > new_init_bal:
            new_cur_bal = new_init_bal

        if rev_cur_bal > rev_init_bal:
            rev_cur_bal = rev_init_bal

        return {
            "new": round(float(1 - (new_cur_bal / new_init_bal)), 5) if not new_init_bal == 0 else 1,
            "rev": round(float(1 - (rev_cur_bal / rev_init_bal)), 5) if not rev_init_bal == 0 else 1
        }


class TradeCommander:
    @staticmethod
    def to_dict(time: int, streamer_mctu: float, condition: Condition, threshold: Threshold):
        return {
            "time": time,
            "streamer_mctu": streamer_mctu,
            "execute_trade": {
                "new": condition.trade_execution_decider(condition.NEW),
                "rev": condition.trade_execution_decider(condition.REV)
            },
            "condition": {
                "is_settlement": condition.is_settlement,
                "new": {
                    "is_time_flow_above_exhaust": condition.NEW["is_time_flow_above_exhaust"],
                    "is_oppty": condition.NEW["is_oppty"],
                    "is_royal_spread": condition.NEW["is_royal"],
                },
                "rev": {
                    "is_time_flow_above_exhaust": condition.REV["is_time_flow_above_exhaust"],
                    "is_oppty": condition.REV["is_oppty"],
                    "is_royal_spread": condition.REV["is_royal"],
                }
            },
            "threshold": {
                "new": {
                    "normal": threshold.NEW["normal"],
                    "royal": threshold.NEW["royal"]
                },
                "rev": {
                    "normal": threshold.REV["normal"],
                    "royal": threshold.REV["royal"]
                }
            },
        }
