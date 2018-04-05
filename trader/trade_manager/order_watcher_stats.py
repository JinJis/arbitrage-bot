import time
import logging
from queue import Queue
from enum import Enum
from threading import Thread


class OperationType(Enum):
    STARTED = "started"
    DONE = "done"
    DELAYED = "delayed"
    ERROR = "error"


class Operation:
    def __init__(self, op_type: OperationType, order_id: str):
        self.timestamp = time.time()
        self.op_type = op_type
        self.order_id = order_id


class OrderWatcherStats(Thread):
    _init_flag = False
    _instance = None

    @classmethod
    def initialize(cls):
        if cls._instance is None:
            cls._init_flag = True
            cls._instance = cls()
            # start thread
            cls._instance.start()
        else:
            raise Exception("OrderWatcherStats already initialized!")

    @classmethod
    def instance(cls) -> "OrderWatcherStats":
        if cls._instance is not None:
            return cls._instance
        else:
            raise Exception("OrderWatcherStats not yet initialized!")

    def __init__(self):
        if (not self._init_flag) or (self._instance is not None):
            raise Exception("`initialize` or `instance` should be called instead!")
        self._active = []

        # stat variables
        self._total_order_count = 0
        self._total_delayed_count = 0
        self._total_done_count = 0
        self._total_error_count = 0
        self._spent_time_avg = 0

        self.operation_queue = Queue()
        self.stop_flag = False
        super().__init__()

    @classmethod
    def started(cls, order_id: str):
        cls.instance().operation_queue.put(
            Operation(OperationType.STARTED, order_id)
        )

    @classmethod
    def done(cls, order_id: str):
        cls.instance().operation_queue.put(
            Operation(OperationType.DONE, order_id)
        )

    @classmethod
    def delayed(cls, order_id: str):
        cls.instance().operation_queue.put(
            Operation(OperationType.DELAYED, order_id)
        )

    @classmethod
    def error(cls, order_id: str):
        cls.instance().operation_queue.put(
            Operation(OperationType.ERROR, order_id)
        )

    def _find_item(self, order_id: str):
        for item in self._active:
            if item["order_id"] == order_id:
                return item
        logging.critical("Could not find item with specified id: %s!" % order_id)

    def _process_operation(self, operation: Operation):
        if operation.op_type is OperationType.STARTED:
            self._active.append({
                "timestamp": operation.timestamp,
                "order_id": operation.order_id
            })
            self._total_order_count += 1
        elif operation.op_type is OperationType.DONE:
            item = self._find_item(operation.order_id)
            if item:
                spent_time = operation.timestamp - item["timestamp"]
                self._spent_time_avg = (self._spent_time_avg * self._total_done_count + spent_time) \
                                       / (self._total_done_count + 1)
                self._active.remove(item)
                self._total_done_count += 1
        elif operation.op_type is OperationType.DELAYED:
            item = self._find_item(operation.order_id)
            if item:
                item["is_delayed"] = True
                self._total_delayed_count += 1
        elif operation.op_type is OperationType.ERROR:
            item = self._find_item(operation.order_id)
            if item:
                self._active.remove(item)
                self._total_error_count += 1
        else:
            raise Exception("Invalid OperationType has set!")

    def get_stats(self):
        return {
            "current_active_count": len(self._active),
            "current_delayed_count": len(self.get_current_delayed()),
            "spent_time_avg": self._spent_time_avg,
            "total_order_count": self._total_order_count,
            "total_done_count": self._total_done_count,
            "total_error_count": self._total_error_count,
            "total_delayed_count": self._total_delayed_count
        }

    def get_current_delayed(self):
        return list([item for item in self._active if item.get("is_delayed", False)])

    def run(self):
        while not self.stop_flag:
            while not self.operation_queue.empty():
                operation = self.operation_queue.get()
                self._process_operation(operation)
            time.sleep(0.1)

    def tear_down(self):
        self.stop_flag = True
        # remove reference
        OrderWatcherStats._instance = None
