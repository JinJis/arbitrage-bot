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
    config.read("config.ini")

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


def run_threaded(job_func, args=()):
    job_thread = threading.Thread(target=job_func, args=args)
    job_thread.start()


def handle_exit():
    print("Collector Bot stopped at " + time.ctime())
    sys.exit(0)


def handle_sigterm(signal, frame):
    handle_exit()


# init collector
mongodb_uri = read_mongodb_uri()
# currency param should be a lower-cased currency symbol listed in api.currency
collector = Collector(mongodb_uri, "eth")


def every_5_sec():
    request_time = int(time.time())
    run_threaded(collector.collect_co_ticker, [request_time])
    run_threaded(collector.collect_co_orderbook, [request_time])
    run_threaded(collector.collect_kb_ticker, [request_time])
    run_threaded(collector.collect_kb_orderbook, [request_time])


def every_hour():
    run_threaded(collector.collect_co_filled_orders)
    run_threaded(collector.collect_kb_filled_orders)


schedule.every(5).seconds.do(every_5_sec)
# schedule.every().hour.do(every_hour)

signal.signal(signal.SIGTERM, handle_sigterm)

# run initial
print("Collector Bot started at " + time.ctime())
schedule.run_all()

while True:
    try:
        schedule.run_pending()
    except KeyboardInterrupt:
        handle_exit()
