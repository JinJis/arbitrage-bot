import sys
import time
from config.global_conf import Global
from collector.scheduler.api_scheduler import ApiScheduler
from collector.scheduler.base_scheduler import BaseScheduler


class TickerOrderbookScheduler(ApiScheduler):
    @BaseScheduler.interval_waiter(5)
    def _actual_run_in_loop(self):
        request_time = int(time.time())

        # Global.run_threaded(self.co_collector.collect_orderbook, [request_time])
        # Global.run_threaded(self.kb_collector.collect_orderbook, [request_time])
        # Global.run_threaded(self.go_collector.collect_orderbook, [request_time])
        Global.run_threaded(self.oc_collector.collect_orderbook, [request_time])
        # Coinnest만 xrp 없음!!
        Global.run_threaded(self.cn_collector.collect_orderbook, [request_time])


if __name__ == "__main__":
    for coin in ["bch", "btc", "eth", "ltc", "qtum"]:
        TickerOrderbookScheduler(coin).run()
