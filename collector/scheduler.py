from .collector import Collector
import threading
import schedule
import time
import urllib.parse
import signal
import sys

is_remote = True


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def handle_exit():
    print("Collector Bot stopped at " + time.ctime())
    sys.exit(0)


def handle_sigterm(signal, frame):
    handle_exit()


# local
mongo_host = "mongodb://127.0.0.1"

# remote
if is_remote:
    username = urllib.parse.quote_plus("bot1")
    password = urllib.parse.quote_plus("GeTrIcHyO111!")
    mongo_host = "mongodb://%s:%s@127.0.0.1" % (username, password)

# init collector
collector = Collector(mongo_host, "eth")

# coinone
schedule.every(5).seconds.do(run_threaded, collector.collect_co_ticker)
schedule.every(5).seconds.do(run_threaded, collector.collect_co_orderbook)
schedule.every().hour.do(run_threaded, collector.collect_co_filled_orders)

# korbit
schedule.every(5).seconds.do(run_threaded, collector.collect_kb_ticker)
schedule.every(5).seconds.do(run_threaded, collector.collect_kb_orderbook)
schedule.every().hour.do(run_threaded, collector.collect_kb_filled_orders)

signal.signal(signal.SIGTERM, handle_sigterm)

# run initial
print("Collector Bot started at " + time.ctime())
schedule.run_all()

while True:
    try:
        schedule.run_pending()
    except KeyboardInterrupt:
        handle_exit()
