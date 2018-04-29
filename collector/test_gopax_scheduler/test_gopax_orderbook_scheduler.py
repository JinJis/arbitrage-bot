import sys
import time

from collector.test_gopax_scheduler.test_gopax_api_scheduler import ApiScheduler2
from collector.scheduler.base_scheduler import BaseScheduler
from config.global_conf import Global


class TickerOrderbookScheduler2(ApiScheduler2):
    @BaseScheduler.interval_waiter(5)
    def _actual_run_in_loop(self):
        request_time = int(time.time())
        Global.run_threaded(self.go_collector.collect_ticker, [request_time])
        Global.run_threaded(self.go_collector.collect_orderbook, [request_time])


if __name__ == "__main__":
    TickerOrderbookScheduler2(sys.argv[1]).run()
t