import time


class SwitchOver:
    def __init__(self, _from: str, _to: str, last_trade_ts: int):
        current_ts = int(time.time())
        self._data = {
            "timestamp": current_ts,
            "from": _from,
            "to": _to,
            "spent_time": (current_ts - last_trade_ts)
        }

    def to_dict(self):
        return dict(self._data)

    def get(self, key: str):
        return self._data[key]
