from config.shared_mongo_client import SharedMongoClient
from collector.rev_ledger_to_xlsx import RevLedgerXLSX

SharedMongoClient.initialize(should_use_localhost_db=False)
RevLedgerXLSX("trx", "coinone", "okcoin").run(mode_status="settlement")
