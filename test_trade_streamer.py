import numpy
import logging
from run_iyo_short_term import main
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient

Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
SharedMongoClient.initialize(should_use_localhost_db=True)

st_local = "2018.08.17 20:48:10"
et_local = "2018.08.18 20:48:10"

iyo_result = main("btc", st_local, et_local)

# make yield list by IYO
yield_batch = []
for iyo_opt in iyo_result:
    yield_batch.append(iyo_opt["yield"])

yield_avg = numpy.average(yield_batch)
yield_std = numpy.std(yield_batch)
print(yield_avg)
print(yield_std)

