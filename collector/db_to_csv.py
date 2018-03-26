from config.global_conf import Global
from pymongo import MongoClient
from .csv_writer import CsvWriter


class DbToCsv:
    ticker_columns = ("timestamp", "high", "low", "last", "volume", "requestTime")

    def __init__(self, is_from_local: bool = True):
        mongodb_uri = Global.read_mongodb_uri(is_from_local)
        self.mongo_client = MongoClient(mongodb_uri)

    def save_ticker_as_csv(self, target_db: str, target_currency: str, start_time: int, end_time: int):
        # ex) target_db = "korbit", target_currency = "eth"
        target_col = self.mongo_client[target_db][target_currency + "_ticker"]
        cursor = target_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }})

        csv_writer = CsvWriter("ticker", "%s_ticker_%d_%d" % (target_currency, start_time, end_time),
                               self.ticker_columns)

        for item in cursor:
            csv_writer.write_joinable([item[key] for key in self.ticker_columns])

        csv_writer.close()
