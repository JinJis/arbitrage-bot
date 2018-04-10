import time
import signal
import sys
import logging
from config.global_conf import Global
from abc import ABC, abstractmethod


class BaseScheduler(ABC):
    def __init__(self):
        # init root logger
        Global.configure_default_root_logging()
        # set the log level for the schedule
        # in order not to display any extraneous log
        logging.getLogger("schedule").setLevel(logging.CRITICAL)

        # add SIGTERM handler
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    @staticmethod
    def handle_exit():
        logging.info("Collector Bot stopped at " + time.ctime())
        sys.exit(0)

    @staticmethod
    def handle_sigterm(signal, frame):
        BaseScheduler.handle_exit()

    @staticmethod
    def interval_waiter(interval_time_sec: int):
        def interval_waiter_decorator(func):
            def interval_function(*args, **kwargs):
                start_time = time.time()
                func(*args, **kwargs)
                end_time = time.time()
                wait_time = interval_time_sec - (end_time - start_time)
                if wait_time > 0:
                    time.sleep(wait_time)

            return interval_function

        return interval_waiter_decorator

    @abstractmethod
    def _actual_run_in_loop(self):
        pass

    def run(self):
        logging.info("Collector Bot started at " + time.ctime())
        while True:
            try:
                self._actual_run_in_loop()
            except KeyboardInterrupt:
                self.handle_exit()
