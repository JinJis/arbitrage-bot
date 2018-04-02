from .scheduler_base import SchedulerBase
from config.global_conf import Global


class SchedulerOneHour(SchedulerBase):
    @SchedulerBase.interval_waiter(60 * 60)
    def _actual_run_in_loop(self):
        Global.run_threaded(self.collector.collect_co_filled_orders)
        Global.run_threaded(self.collector.collect_kb_filled_orders)


if __name__ == "__main__":
    SchedulerOneHour().run()
