from trader.market.trade import Trade, TradeTag
from trader.market.switch_over import SwitchOver
import numpy


# TODO: should process db logging, manage(& track) order, balance & tradings(new / reverse)
# use Global.get_unique_process_tag
class TradeManager:
    def __init__(self):
        self._trade_list = list()
        self._switch_over_list = list()

    def add_trade(self, trade: Trade):
        # check last & current trade tag
        last_trade = self.get_last_trade()
        last_trade_tag = last_trade.trade_tag if last_trade is not None else None
        cur_trade_tag = trade.trade_tag
        last_switch_over = self.get_last_switch_over()

        # if the trade tag has changed and this is not the first trade
        if cur_trade_tag is not last_trade_tag and last_switch_over is not None:
            # create switch over instance & add into list
            last_trade_tag_name = getattr(last_trade_tag, "name", "None")
            cur_trade_tag_name = getattr(cur_trade_tag, "name", "None")
            last_switch_over_ts = last_switch_over.get("timestamp")
            switch_over = SwitchOver(last_trade_tag_name, cur_trade_tag_name, last_switch_over_ts)
            self.add_switch_over(switch_over)

        self._trade_list.append(trade)

    def add_switch_over(self, switch_over: SwitchOver):
        self._switch_over_list.append(switch_over)

    def get_trade_count(self, target_trade_tag: TradeTag = None):
        if target_trade_tag is None:
            return len(self._trade_list)
        else:
            return sum(1 for trade in self._trade_list if trade.trade_tag is target_trade_tag)

    def get_last_trade(self):
        return self._trade_list[-1] if len(self._trade_list) > 0 else None

    def get_last_switch_over(self):
        return self._switch_over_list[-1] if len(self._switch_over_list) > 0 else None

    def get_average_switch_over_spent_time(self):
        spent_time_list = [switch_over.get("spent_time") for switch_over in self._switch_over_list]
        return numpy.mean(spent_time_list) if len(spent_time_list) > 0 else 0

    def get_switch_over_count(self):
        return len(self._switch_over_list)

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
