import time
from .scheduler_base import SchedulerBase
from config.global_conf import Global


class SchedulerFiveSec(SchedulerBase):
    @SchedulerBase.interval_waiter(5)
    def _actual_run_in_loop(self):
        request_time = int(time.time())
        Global.run_threaded(self.collector.collect_co_ticker, [request_time])
        Global.run_threaded(self.collector.collect_co_orderbook, [request_time])
        Global.run_threaded(self.collector.collect_kb_ticker, [request_time])
        Global.run_threaded(self.collector.collect_kb_orderbook, [request_time])


if __name__ == "__main__":
    SchedulerFiveSec().run()
