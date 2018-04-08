from config.global_conf import Global
from collector.db_to_csv import DbToCsv

db_to_csv = DbToCsv(False)
start_time = Global.convert_local_datetime_to_epoch("2018.04.06 10:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.04.06 22:00:00", timezone="kr")

"""Get Orderbook"""
# db_to_csv.save_processed_info("coinone", "eth", start_time, end_time)
# db_to_csv.save_processed_info("korbit", "eth", start_time, end_time)

"""Get Ticker"""
# db_to_csv.save_ticker_as_csv("coinone", "eth", start_time, end_time)
# db_to_csv.save_ticker_as_csv("korbit", "eth", start_time, end_time)

"""Get VWAP mid price"""
# db_to_csv.save_mid_vwap_mid_price("coinone", "eth", start_time, end_time, 5)
# db_to_csv.save_mid_vwap_mid_price("korbit", "eth", start_time, end_time, 5)

"""Korbit timestamp not normalized, it's in ms unit"""
# db_to_csv.save_filled_orders_as_csv("korbit", "eth", start_time * 1000, end_time * 1000)

"""Orderbook_index"""

db_to_csv.save_orderbook_index("coinone", "eth", start_time, end_time, 5)
