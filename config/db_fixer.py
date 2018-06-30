import logging
from itertools import zip_longest
from config.shared_mongo_client import SharedMongoClient


class DbFixer:
    @staticmethod
    def update_rq_diff_by_control_db(con_db: str, con_col: str, tar_db: str, tar_col: str,
                                     start_time: int, end_time: int):
        db_client = SharedMongoClient.instance()
        control_col = db_client[con_db][con_col]
        target_col = db_client[tar_db][tar_col]

        con_cursor = control_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])
        tar_cursor = target_col.find({"requestTime": {
            "$gte": start_time,
            "$lte": end_time
        }}).sort([("requestTime", 1)])

        con_count = con_cursor.count()
        tar_count = tar_cursor.count()

        logging.info("Cursor count: a %d, b %d" % (con_count, tar_count))

        is_first_occur = False

        for con_item, tar_item in zip_longest(con_cursor, tar_cursor):
            con_rt = con_item["requestTime"]
            tar_rt = tar_item["requestTime"]
            if con_rt != tar_rt:
                logging.info("Diff: control_rt %d, target_rt %d " % (con_rt, tar_rt))
                if not is_first_occur:
                    raise Exception("At least the first occurrence should be a valid pair!")
                rq_diff = con_rt - tar_rt
                adjusted_rq = tar_rt + rq_diff
                logging.info("Adding %d item in target_col..." % tar_rt)
                target_col.update_one({"_id": tar_item["_id"]}, {"$set": {"requestTime": adjusted_rq}})
            else:
                is_first_occur = True

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
