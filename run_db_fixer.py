from config.shared_mongo_client import SharedMongoClient
from config.db_fixer import DbFixer
from config.global_conf import Global

Global.configure_default_root_logging()
SharedMongoClient.initialize(should_use_localhost_db=False)
DbFixer.add_missing_item_with_plain_copy_prev("coinone", "eth_orderbook", "korbit", "eth_orderbook",
                                              1523454835, 1523455200)
