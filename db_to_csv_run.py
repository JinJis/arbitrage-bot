from config.global_conf import Global
from collector.db_to_csv import DbToCsv

db_to_csv = DbToCsv(False)
start_time = Global.convert_local_datetime_to_epoch("2018.04.06 10:00:00", timezone="kr")
end_time = Global.convert_local_datetime_to_epoch("2018.04.06 22:00:00", timezone="kr")
db_to_csv.save_processed_info("korbit", "eth", start_time, end_time)
