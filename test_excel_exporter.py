from collector.rfab_ledger_to_xlsx import RFABLedgerXLSX
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient

SharedMongoClient.initialize(should_use_localhost_db=False)
start_time = Global.convert_local_datetime_to_epoch("2018.10.06 14:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.10.06 18:45:00", timezone="kr")
RFABLedgerXLSX("eos", "coinone", "gopax", start_time, end_time, is_test=False).run()
