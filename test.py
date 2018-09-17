from config.shared_mongo_client import SharedMongoClient
from collector.rev_ledger_to_xlxs import RevLedgerXLXS

SharedMongoClient.initialize(should_use_localhost_db=False)
RevLedgerXLXS("btc", "coinone", "okcoin").run(mode_status="initiation")
