import logging
from config.shared_mongo_client import SharedMongoClient
from config.db_fixer import DbFixer
from config.global_conf import Global

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=False)
start_time = Global.convert_local_datetime_to_epoch("2018.08.16 00:44:14", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.08.16 01:14:14", timezone="kr")

# DbFixer.add_missing_item_with_plain_copy_prev("coinone", "bch_orderbook", "gopax", "bch_orderbook",
#                                               start_time, end_time)
# DbFixer.fill_empty_orderbook_entry("gopax", "bch_orderbook", start_time, end_time)
# DbFixer.update_rq_diff_by_control_db("coinone", "bch_orderbook", "gopax", "bch_orderbook",
#                                      start_time, end_time)

"""IYO 돌릴때 사용하는 것들"""

DbFixer.match_request_time_in_orderbook_entry("bithumb", "gopax", "bch_orderbook", start_time, end_time)
