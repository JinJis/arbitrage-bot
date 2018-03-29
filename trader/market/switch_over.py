import time


class SwitchOver:
    def __init__(self, _from: str, _to: str, last_ts: int, cur_ts: int):
        self._data = {
            "timestamp": cur_ts,
            "from": _from,
            "to": _to,
            "spent_time": (cur_ts - last_ts)
        }

    def to_dict(self):
        return dict(self._data)

    def get(self, key: str):
        return self._data[key]
