from config.shared_mongo_client import SharedMongoClient
from config.db_fixer import DbFixer
from config.global_conf import Global

Global.configure_default_root_logging()
SharedMongoClient.initialize(should_use_localhost_db=False)
# DbFixer.add_missing_item_with_plain_copy_prev("coinone", "eth_orderbook", "korbit", "eth_orderbook",
#                                               1523454835, 1523455200)

start_time = Global.convert_local_datetime_to_epoch("2018.05.01 10:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.05.02 10:00:00", timezone="kr")
DbFixer.fill_empty_orderbook_entry("gopax", "btc_orderbook", start_time, end_time)
