class UserCreation:
    def __init__(self, _user_id: str):
        self.USER_COL_DICT = {
            "user_id": _user_id
        }
        self.STREAMER_COL_DICT = {
            "user_id": _user_id,
            "balance_tracker": {},
            "trade_commander": {},
            "success_trade_recorder": {},
            "failed_trade_recorder": {}
        }
        self.HISTORY_COL_DICT = {
            "user_id": _user_id,
            "direct_invest_history": {},
            "transfer_history": {},
            "trade_history": {}
        }


class RFABValidation:
    BALANCE_TRACKER_DICT = {
        "time": None,
        "target_currency": None,
        "mm1_name": None,
        "mm2_name": None,
        "initial_bal": {
            "krw": {
                "mm1": None,
                "mm2": None,
                "total": None
            },
            "coin": {
                "mm1": None,
                "mm2": None,
                "total": None
            }
        },
        "current_bal": {
            "krw": {
                "mm1": None,
                "mm2": None,
                "total": None
            },
            "coin": {
                "mm1": None,
                "mm2": None,
                "total": None
            }
        }
    }

    TRADE_COMMANDER_DICT = {
        "time": None,
        "streamer_mctu": None,
        "execute_trade": {
            "new": None,
            "rev": None
        },
        "condition": {
            "is_settlement": None,
            "new": {
                "is_time_flow_above_exhaust": None,
                "is_oppty": None,
                "is_royal_spread": None,
            },
            "rev": {
                "is_time_flow_above_exhaust": None,
                "is_oppty": None,
                "is_royal_spread": None,
            }
        },
        "threshold": {
            "new": {
                "normal": None,
                "royal": None
            },
            "rev": {
                "normal": None,
                "royal": None
            }
        },
    }

    SUCCESS_TRADE_RECORDER = []
    FAILED_TRADE_RECORDER = []
