from config.global_conf import Global
from pymongo import MongoClient
from .csv_writer import CsvWriter
from analyzer.analyzer import Analyzer


class DbToCsv:
    ticker_columns = ("timestamp", "high", "low", "last", "volume", "requestTime")
    filled_orders_columns = ("timestamp", "price", "amount")

    def __init__(self, should_use_localhost_db: bool):
        mongodb_uri = Global.read_mongodb_uri(should_use_localhost_db)
        self.mongo_client = MongoClient(mongodb_uri)

    def save_any_flat_col_as_csv(self, target_db: str, target_col: str, time_col_name: str,
                                 start_time: int, end_time: int, columns: tuple):
        col = self.mongo_client[target_db][target_col]
        cursor = col.find({time_col_name: {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([(time_col_name, 1)])

        csv_writer = CsvWriter("stat", "%s_%s_%d_%d" % (target_db, target_col, start_time, end_time), columns)

        for item in cursor:
            csv_writer.write_joinable([item[key] for key in columns])

        csv_writer.close()

    def save_ticker_as_csv(self, target_db: str, target_currency: str, start_time: int, end_time: int):
        self.save_any_flat_col_as_csv(target_db, target_currency + "_ticker", "requestTime", start_time, end_time,
                                      DbToCsv.ticker_columns)

    def save_filled_orders_as_csv(self, target_db: str, target_currency: str, start_time: int, end_time: int):
        self.save_any_flat_col_as_csv(target_db, target_currency + "_filled_orders", "timestamp",
                                      start_time, end_time, DbToCsv.filled_orders_columns)

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

    def save_mid_vwap_mid_price(self, target_db: str, target_currency: str, start_time: int, end_time: int, depth: int):
        orderbook_col = self.mongo_client[target_db][target_currency + "_orderbook"]
        orderbook_cursor = orderbook_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        csv_writer = CsvWriter("stat", "%s_%s_mid_vwap_%d_%d_%d_depth" %
                               (target_db, target_currency, start_time, end_time, depth),
                               ("request_time", "mid_price", "mid_vwap", "ask_vwap", "bid_vwap", "minask", "maxbid"))

        for orderbook in orderbook_cursor:
            request_time = int(orderbook["requestTime"])
            mid_price, minask, maxbid = Analyzer.get_orderbook_mid_price(orderbook)
            mid_vwap, ask_vwap, bid_vwap = Analyzer.get_orderbook_mid_vwap(orderbook, depth)
            csv_writer.write_joinable((request_time, mid_price, mid_vwap, ask_vwap, bid_vwap, minask, maxbid))

        csv_writer.close()
