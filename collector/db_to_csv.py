from config.global_conf import Global
from pymongo import MongoClient
from .csv_writer import CsvWriter
from analyzer.analyzer import Analyzer


class DbToCsv:
    ticker_columns = ("timestamp", "high", "low", "last", "volume", "requestTime")

    def __init__(self, should_use_localhost_db: bool):
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db)
        self.mongo_client = MongoClient(mongodb_uri)

    def save_ticker_as_csv(self, target_db: str, target_currency: str, start_time: int, end_time: int):
        # ex) target_db = "korbit", target_currency = "eth"
        target_col = self.mongo_client[target_db][target_currency + "_ticker"]
        cursor = target_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        csv_writer = CsvWriter("ticker", "%s_%s_ticker_%d_%d" % (target_db, target_currency, start_time, end_time),
                               self.ticker_columns)

        for item in cursor:
            csv_writer.write_joinable([item[key] for key in self.ticker_columns])

        csv_writer.close()

    def save_processed_info(self, target_db: str, target_currency: str, start_time: int, end_time: int):
        ticker_col = self.mongo_client[target_db][target_currency + "_ticker"]
        orderbook_col = self.mongo_client[target_db][target_currency + "_orderbook"]
        ticker_cursor = ticker_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])
        orderbook_cursor = orderbook_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        ticker_count = ticker_cursor.count()
        orderbook_count = orderbook_cursor.count()

        csv_writer = CsvWriter("stat", "%s_%s_processed_%d_%d" % (target_db, target_currency, start_time, end_time),
                               ("requestTime", "ticker", "midPrice", "minAsk", "maxBid"))

        if ticker_count != orderbook_count:
            Global.request_time_validation_on_cursor_count_diff(ticker_cursor, orderbook_cursor)

        for ticker, orderbook in zip(ticker_cursor, orderbook_cursor):
            request_time = int(ticker["requestTime"])
            last = int(ticker["last"].to_decimal())
            mid_price, minask, maxbid = Analyzer.get_orderbook_mid_price(orderbook)
            csv_writer.write_joinable((request_time, last, mid_price, minask, maxbid))

        csv_writer.close()
