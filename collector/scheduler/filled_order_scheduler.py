from collector.scheduler.api_scheduler import ApiScheduler
from collector.scheduler.api_scheduler import BaseScheduler
from config.global_conf import Global


class FilledOrderScheduler(ApiScheduler):
    @BaseScheduler.interval_waiter(3)
    def _actual_run_in_loop(self):
        Global.run_threaded(self.co_collector.collect_filled_orders)
        Global.run_threaded(self.kb_collector.collect_filled_orders)


if __name__ == "__main__":
    FilledOrderScheduler("eth").run()
