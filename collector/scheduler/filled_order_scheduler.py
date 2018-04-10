from collector.filled_order_collector import FilledOrderCollector
from collector.scheduler.base_scheduler import BaseScheduler
from config.global_conf import Global


class FilledOrderScheduler(BaseScheduler):
    def __init__(self, should_use_localhost_db: bool = True):
        super().__init__()
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db)
        self.collector = FilledOrderCollector(mongodb_uri, "eth")

    @BaseScheduler.interval_waiter(5)
    def _actual_run_in_loop(self):
        Global.run_threaded(self.collector.collect_kb_filled_orders)


if __name__ == "__main__":
    FilledOrderScheduler().run()
