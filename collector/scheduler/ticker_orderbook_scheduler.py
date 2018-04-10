import time
from collector.collector import Collector
from collector.scheduler.base_scheduler import BaseScheduler
from config.global_conf import Global


class TickerOrderbookScheduler(BaseScheduler):
    def __init__(self, should_use_localhost_db: bool = True):
        super().__init__()
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db)
        self.collector = Collector(mongodb_uri, "eth")

    @BaseScheduler.interval_waiter(5)
    def _actual_run_in_loop(self):
        request_time = int(time.time())
        Global.run_threaded(self.collector.collect_co_ticker, [request_time])
        Global.run_threaded(self.collector.collect_co_orderbook, [request_time])
        Global.run_threaded(self.collector.collect_kb_ticker, [request_time])
        Global.run_threaded(self.collector.collect_kb_orderbook, [request_time])


if __name__ == "__main__":
    TickerOrderbookScheduler().run()
