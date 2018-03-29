import time


class SwitchOver:
    def __init__(self, _from: str, _to: str, last_switch_over_timestamp: int):
        cur_timestamp = int(time.time())
        self._data = {
            "timestamp": cur_timestamp,
            "from": _from,
            "to": _to,
            "spent_time": (cur_timestamp - last_switch_over_timestamp)
        }

    def to_dict(self):
        return dict(self._data)

    def get_spent_time(self):
        return self._data["spent_time"]
