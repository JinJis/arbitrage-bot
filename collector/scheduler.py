from .collector import Collector
import threading
import schedule
import time
import urllib.parse
import signal
import sys
import configparser


def read_mongodb_uri():
    config = configparser.ConfigParser()
    mongo = config["MONGO"]
    host = mongo["Host"]
    port = mongo.getint("Port")
    use_auth = mongo.getboolean("UseAuth")

    if use_auth:
        username = urllib.parse.quote_plus(mongo["Username"])
        password = urllib.parse.quote_plus(mongo["Password"])
        return "mongodb://%s:%s@%s:%d" % (username, password, host, port)
    else:
        return "mongodb://%s:%d" % (host, port)


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def handle_exit():
    print("Collector Bot stopped at " + time.ctime())
    sys.exit(0)


def handle_sigterm(signal, frame):
    handle_exit()


# init collector
mongodb_uri = read_mongodb_uri()
collector = Collector(mongodb_uri, "eth")

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
