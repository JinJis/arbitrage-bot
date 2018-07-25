import logging
from itertools import zip_longest
from pymongo.cursor import Cursor
from config.shared_mongo_client import SharedMongoClient


class DbFixer:
    @staticmethod
    def add_missing_item_with_plain_copy_prev(a_db: str, a_col: str, b_db: str, b_col: str,
                                              start_time: int, end_time: int):
        db_client = SharedMongoClient.instance()
        a_target_col = db_client[a_db][a_col]
        b_target_col = db_client[b_db][b_col]

        redefined_start_time = start_time

        while True:
            retry_flag = False

            a_cursor = a_target_col.find({"requestTime": {
                "$gte": redefined_start_time,
                "$lte": end_time
            }}).sort([("requestTime", 1)])
            b_cursor = b_target_col.find({"requestTime": {
                "$gte": redefined_start_time,
                "$lte": end_time
            }}).sort([("requestTime", 1)])

            a_count = a_cursor.count()
            b_count = b_cursor.count()

            logging.info("Cursor count: a %d, b %d" % (a_count, b_count))

            last_a_item = None
            last_b_item = None

            for a_item, b_item in zip_longest(a_cursor, b_cursor):
                a_rt = a_item["requestTime"]
                b_rt = b_item["requestTime"]
                if a_rt != b_rt:
                    logging.info("Diff: a_rt %d, b_rt %d " % (a_rt, b_rt))
                    if last_a_item is None or last_b_item is None:
                        raise Exception("At least the first occurrence should be a valid pair!")
                    is_b_older = a_rt > b_rt
                    if is_b_older:
                        last_a_item["requestTime"] = b_rt
                        logging.info("Adding %d item in a_col..." % b_rt)
                        a_target_col.insert_one(last_a_item)
                    else:
                        # if a is older
                        last_b_item["requestTime"] = a_rt
                        logging.info("Adding %d item in b_col..." % a_rt)
                        b_target_col.insert_one(last_b_item)
                    # redefine start time for cursor re-request
                    redefined_start_time = min(a_rt, b_rt)
                    retry_flag = True
                    break
                else:
                    last_a_item = dict(a_item)
                    del last_a_item["_id"]
                    last_b_item = dict(b_item)
                    del last_b_item["_id"]

            if retry_flag:
                a_cursor.close()
                b_cursor.close()
                continue
            else:
                break

    @staticmethod
    def fill_empty_orderbook_entry(a_db: str, a_col: str, start_time: int, end_time: int):
        db_client = SharedMongoClient.instance()
        a_target_col = db_client[a_db][a_col]

        a_cursor = a_target_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        prev_item = None
        for item in a_cursor:
            if len(item["asks"]) == 0 or len(item["bids"]) == 0:
                print(item["requestTime"])
                if prev_item is None:
                    raise Exception("At least first item should not be None")
                else:
                    item["asks"] = prev_item["asks"]
                    item["bids"] = prev_item["bids"]
                    SharedMongoClient._async_update(
                        a_target_col,
                        {"requestTime": item["requestTime"]},
                        {"$set": item}
                    )
            prev_item = item

    @staticmethod
    def match_request_time_in_orderbook_entry(control_db: str, target_db: str, col_name: str,
                                              start_time: int, end_time: int):
        db_client = SharedMongoClient.instance()
        control_col = db_client[control_db][col_name]
        target_col = db_client[target_db][col_name]

        ctrl_data_set = control_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        # get first nearest request time from control db
        first_ctrl_rq = ctrl_data_set[0]["requestTime"]

        # get first and second request time from target db
        trgt_data_set = list(target_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])[:2])

        # first target requestTime
        first_trgt_rq = trgt_data_set[0]["requestTime"]
        # second target requestTime
        second_trgt_rq = trgt_data_set[1]["requestTime"]

        # calc difference between control reqTime and target reqTimes
        ctrl_first_trgt_first_diff = abs(first_ctrl_rq - first_trgt_rq)
        ctrl_first_trgt_second_diff = abs(first_ctrl_rq - second_trgt_rq)

        # if first in target is nearer to first in control, set first in target as starting point
        if ctrl_first_trgt_first_diff < ctrl_first_trgt_second_diff:
            trgt_start_rq = first_trgt_rq
        # if second in target is nearer to first in control, set second in target as starting point
        elif ctrl_first_trgt_first_diff > ctrl_first_trgt_second_diff:
            trgt_start_rq = second_trgt_rq
        else:
            raise Exception("Difference is same, please Manually check the database and fix!!")

        # get count of data from control db
        ctrl_data_count = ctrl_data_set.count()

        # get same count of data from target db with the starting point as start time and without end time
        trgt_data_set: Cursor = target_col.find({"requestTime": {
            "$gte": trgt_start_rq
        }}).sort([("requestTime", 1)]).limit(ctrl_data_count)
        trgt_data_count = trgt_data_set.count(with_limit_and_skip=True)

        logging.info("ctrl count count: %d, trgt: %d" % (ctrl_data_count, trgt_data_count))
        assert (ctrl_data_count == trgt_data_count)

        last_index = ctrl_data_count - 1
        ctrl_last_rq = ctrl_data_set[last_index]["requestTime"]
        trgt_last_rq = trgt_data_set[last_index]["requestTime"]
        assert (abs(ctrl_last_rq - trgt_last_rq) < 3)

        # loop through both
        # update target's request time with control's request
        for ctrl_data, trgt_data in zip(ctrl_data_set, trgt_data_set):
            ctrl_rq = ctrl_data["requestTime"]
            trgt_rq = trgt_data["requestTime"]
            logging.info("ctrl_rqt: %d, trgt_rqt: %d" % (ctrl_rq, trgt_rq))
            if trgt_rq == ctrl_rq:
                continue
            SharedMongoClient._async_update(
                target_col,
                {"requestTime": trgt_rq},
                {"$set": {"requestTime": ctrl_rq}}
            )

    @staticmethod
    def check_empty_data_by_rq_time(db_name: str, col_name: str, start_time: int, end_time: int):
        db_client = SharedMongoClient.instance()
        target_col = db_client[db_name][col_name]
        target_data_set = target_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        pre_data = None
        for data in target_data_set:
            if pre_data is None:
                pre_data = data
                continue
            rq_diff = (data["requestTime"] - pre_data["requestTime"])
            if rq_diff <= 7:
                pre_data = data
            else:
                logging.info("RequestTime Difference observed! requestTime_diff: %d Current: %d, Before: %d"
                             % (rq_diff, data["requestTime"], pre_data["requestTime"]))
                pre_data = data
