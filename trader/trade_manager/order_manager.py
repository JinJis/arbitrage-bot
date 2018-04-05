import threading
import time


class OrderManager:

    def __init__(self):
        self._active = []
        self.lock = threading.Lock()

    def add_active(self, order_id: str):
        with self.lock:
            self._active.append({
                "timestamp": time.time(),
                "order_id": order_id
            })

    def remove_active(self, order_id: str):
        with self.lock:
            for item in self._active:
                if item["order_id"] == order_id:
                    self._active.remove(item)

    def get_active(self):
        with self.lock:
            return tuple(self._active)
