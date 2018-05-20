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

    def save_orderbook_index(self, target_db: str, target_currency: str, start_time: int, end_time: int, depth: int):
        orderbook_col = self.mongo_client[target_db][target_currency + "_orderbook"]
        orderbook_cursor = orderbook_col.find({"timestamp": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("timestamp", 1)])

        csv_writer = CsvWriter("stat", "%s_%s_orderbook_indexed_%d_%d_%d_depth" %
                               (target_db, target_currency, start_time, end_time, depth),
                               ("timestamp", "index", "ask_price", "ask_amount", "ask_total_amount", "bid_price",
                                "bid_amount", "bid_total_amount"))

        for item in orderbook_cursor:
            timestamp = item["timestamp"]
            asks = item["asks"]
            bids = item["bids"]
            ask_total_amount_result = 0
            bid_total_amount_result = 0

            for i in range(depth):
                result = [timestamp, i]
                ask = asks[i]
                bid = bids[i]

                if i != depth - 1:
                    for value in (ask, bid):
                        price = int(value["price"].to_decimal())
                        amount = float(value["amount"].to_decimal())
                        result.extend([price, amount, ""])
                        if value is ask:
                            ask_total_amount_result += amount
                        elif value is bid:
                            bid_total_amount_result += amount
                    csv_writer.write_joinable(result)

                elif i == depth - 1:
                    for value in (ask, bid):
                        price = int(value["price"].to_decimal())
                        amount = float(value["amount"].to_decimal())
                        if value is ask:
                            ask_total_amount_result += amount
                            result.extend([price, amount, ask_total_amount_result])
                        elif value is bid:
                            bid_total_amount_result += amount
                            result.extend([price, amount, bid_total_amount_result])
                    csv_writer.write_joinable(result)
        csv_writer.close()

    """RFAB2 - Optimized Traded Spread to CSV"""
    def rfab2_ots_to_csv(self, mm1_db: str, mm2_db: str, mm1_fee: float, mm2_fee: float,
                         target_currency: str, start_time: int, end_time: int, depth: int):
        mm1_orderbook_col = self.mongo_client[mm1_db][target_currency + "_orderbook"]
        mm2_orderbook_col = self.mongo_client[mm2_db][target_currency + "_orderbook"]
        mm1_orderbook_cursor = mm1_orderbook_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])
        mm2_orderbook_cursor = mm2_orderbook_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        csv_writer = CsvWriter("stat", "%s-%s_%s_OTS_in_CSV_%d_%d_%d_max-index" %
                               (mm1_db, mm2_db, target_currency, start_time, end_time, depth),
                               ("requestTime", "Trade type", "Spread in unit", "Buy Price", "Buy Index",
                                "Sell Price", "Sell index", "Tradable Spread", "Tradable Qty"))

        mm1_count = mm1_orderbook_cursor.count()
        mm2_count = mm2_orderbook_cursor.count()


        if mm1_count != mm2_count:
            Global.request_time_validation_on_cursor_count_diff(mm1_orderbook_cursor, mm2_orderbook_cursor)
        else:
            print("# of 'mm1 and mm2 requestTime' matched perfectly!!")

        for mm1_ob, mm2_ob in zip(mm1_orderbook_cursor, mm2_orderbook_cursor):

            requesttime = mm1_ob["requestTime"]
            (new_unit_spread, rev_unit_spread, opt_new_spread, opt_rev_spread,
             opt_new_buy_price, opt_new_buy_index, opt_new_sell_price, opt_new_sell_index, new_traded_qty,
             opt_rev_buy_price, opt_rev_buy_index, opt_rev_sell_price, opt_rev_sell_index, rev_traded_qty) = \
                Analyzer.optimized_tradable_spread_strategy(mm1_ob, mm2_ob, mm1_fee, mm2_fee, depth)

            result = [requesttime]
            if opt_new_spread >= 0:
                result.extend(["NEW", new_unit_spread, opt_new_buy_price, opt_new_buy_index,
                               opt_new_sell_price, opt_new_sell_index, opt_new_spread, new_traded_qty])
                csv_writer.write_joinable(result)
            elif opt_rev_spread >= 0:
                result.extend(["REV", rev_unit_spread, opt_rev_buy_price, opt_rev_buy_index,
                               opt_rev_sell_price, opt_rev_sell_index, opt_rev_spread, rev_traded_qty])
                csv_writer.write_joinable(result)
        csv_writer.close()





