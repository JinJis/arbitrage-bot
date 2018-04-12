import logging
from itertools import zip_longest
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
