from collector import Collector
import threading
import schedule
import time


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


collector = Collector("eth")

# coinone
schedule.every(3).seconds.do(run_threaded, collector.collect_co_ticker)
schedule.every(3).seconds.do(run_threaded, collector.collect_co_orderbook)
schedule.every().hour.do(run_threaded, collector.collect_co_filled_orders)

# korbit
schedule.every(3).seconds.do(run_threaded, collector.collect_kb_ticker)
schedule.every(3).seconds.do(run_threaded, collector.collect_kb_orderbook)
schedule.every().hour.do(run_threaded, collector.collect_kb_filled_orders)

# run initial
print("Collector Bot started at " + time.ctime())
schedule.run_all()

while True:
    try:
        schedule.run_pending()
    except KeyboardInterrupt:
        print("Collector Bot stopped at " + time.ctime())
        exit(0)
