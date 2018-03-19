from .collector import Collector
import threading
import schedule
import time
import urllib.parse
import signal
import sys
import configparser
import logging


class Scheduler:
    def __init__(self):
        # init root logger
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S",
                            stream=sys.stdout)
        # set the log level for the schedule
        # in order not to display any extraneous log
        logging.getLogger("schedule").setLevel(logging.CRITICAL)

        # init collector
        mongodb_uri = self.read_mongodb_uri()
        # currency param should be a lower-cased currency symbol listed in api.currency
        self.collector = Collector(mongodb_uri, "eth")

        # add SIGTERM handler
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    @staticmethod
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

    @staticmethod
    def run_threaded(job_func, args=()):
        job_thread = threading.Thread(target=job_func, args=args)
        job_thread.start()

    @staticmethod
    def handle_exit():
        logging.info("Collector Bot stopped at " + time.ctime())
        sys.exit(0)

    @staticmethod
    def handle_sigterm(signal, frame):
        Scheduler.handle_exit()

    def every_5_sec(self):
        request_time = int(time.time())
        self.run_threaded(self.collector.collect_co_ticker, [request_time])
        self.run_threaded(self.collector.collect_co_orderbook, [request_time])
        self.run_threaded(self.collector.collect_kb_ticker, [request_time])
        self.run_threaded(self.collector.collect_kb_orderbook, [request_time])

    def every_hour(self):
        self.run_threaded(self.collector.collect_co_filled_orders)
        self.run_threaded(self.collector.collect_kb_filled_orders)

    def run(self):
        schedule.every(5).seconds.do(self.every_5_sec)
        schedule.every().hour.do(self.every_hour)

        # run initial
        logging.info("Collector Bot started at " + time.ctime())
        schedule.run_all()

        while True:
            try:
                schedule.run_pending()
            except KeyboardInterrupt:
                self.handle_exit()


if __name__ == "__main__":
    Scheduler().run()
