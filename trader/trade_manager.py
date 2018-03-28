# TODO: should process db logging, manage(& track) order, balance & tradings(new / reverse)
# use Global.get_unique_process_tag
class TradeManager:
    pass

    # if self.should_db_logging:
    #     # init db related
    #     self.mongo_client = MongoClient(Global.read_mongodb_uri())
    #     target_db = self.mongo_client["market_manager_log"]
    #     self.order_col = target_db["order"]
    #     self.filled_order_col = target_db["filled_order"]
    #     self.balance_col = target_db["balance"]

    # def log_order(self, order: Order):
    #     logging.info(order)
    #     if self.should_db_logging:
    #         self.order_col.insert_one(order.to_dict())
    #
    # def log_balance(self):
    #     logging.info(self.balance)
    #     if self.should_db_logging:
    #         self.balance_col.insert_one(self.balance.to_dict())
