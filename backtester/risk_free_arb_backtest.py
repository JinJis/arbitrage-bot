import logging
from pymongo.cursor import Cursor
from analyzer.analyzer import BasicAnalyzer
from analyzer.analyzer import ATSAnalyzer, SpreadInfo
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.trade_manager.trade_manager import TradeManager
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator
from trader.market_manager.virtual_market_manager import VirtualMarketManager


class RfabBacktester:
    TARGET_STRATEGY = ATSAnalyzer.actual_tradable_spread_strategy

    def __init__(self, mm1: VirtualMarketManager, mm2: VirtualMarketManager, target_currency: str):
        self.mm1 = mm1
        self.mm2 = mm2
        self.target_currency = target_currency
        self.init_setting_dict = None
        self.is_init_setting_opt = None

        self.mm1_currency = self.mm1.get_market_currency(self.target_currency)
        self.mm2_currency = self.mm2.get_market_currency(self.target_currency)

        self.trade_manager = TradeManager(should_db_logging=True, is_backtesting=True)
        self.trade_logger = TradeInfoLogger(self.trade_manager, self.target_currency)

        # attributes for InitialSettingOptimizer
        self.total_krw_bal = 0
        self.trade_new = 0
        self.trade_rev = 0

    def run(self, mm1_data_cursor: Cursor, mm2_data_cursor: Cursor,
            init_setting_dict: dict, is_init_setting_opt: bool = False):

        # init settings
        self.init_setting_dict = init_setting_dict
        self.is_init_setting_opt = is_init_setting_opt

        # loop through history data
        for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
            self.actual_trade_loop(mm1_data, mm2_data)
        # log backtesting result
        if not self.is_init_setting_opt:
            self.trade_logger.log_trade_info()
            self.trade_logger.log_oppty_info()
            self.trade_logger.log_combined_balance(self.mm1.balance, self.mm2.balance)
        else:
            self.total_krw_bal = self.get_krw_total_balance()
            self.trade_new = self.trade_manager.get_trade_count(TradeTag.NEW)
            self.trade_rev = self.trade_manager.get_trade_count(TradeTag.REV)

    def add_trade(self, trade: Trade, spread_info: SpreadInfo):
        if not trade:
            return
        self.trade_manager.add_trade(trade)
        if not self.is_init_setting_opt:
            TradeInfoLogger.execute_trade_log_info(trade, spread_info)

    def actual_trade_loop(self, mm1_data: dict, mm2_data: dict):
        # adjust orderbook for realistic backtesting
        self.mm1.apply_history_to_orderbook(mm1_data)
        self.mm2.apply_history_to_orderbook(mm2_data)

        new_trade = None
        rev_trade = None
        spread_info = RfabBacktester.TARGET_STRATEGY(mm1_data, mm2_data, self.mm1.market_fee, self.mm2.market_fee,
                                                     self.init_setting_dict["max_trading_coin"])

        # Dictionary that possess spread information that will be used in trading algorithms
        new_spread_info = spread_info["new"]
        rev_spread_info = spread_info["rev"]

        # NEW
        if new_spread_info.spread_in_unit > 0:
            self.trade_logger.acc_oppty_counter("new")
            new_trade = self.execute_trade(new_spread_info, "new")
            self.add_trade(new_trade, new_spread_info)

        # REVERSE
        if rev_spread_info.spread_in_unit > 0:
            self.trade_logger.acc_oppty_counter("rev")
            rev_trade = self.execute_trade(new_spread_info, "rev")
            self.add_trade(rev_trade, rev_spread_info)

        # if there was any trade
        if new_trade or rev_trade:
            # update each balance
            self.mm1.update_balance()
            self.mm2.update_balance()

    def execute_trade(self, spread_info: SpreadInfo, trade_type: str = "new" or "rev"):
        if trade_type == "new":
            buying_mkt = self.mm1
            selling_mkt = self.mm2
            buying_currency = self.mm1_currency
            selling_currency = self.mm2_currency
        elif trade_type == "rev":
            buying_mkt = self.mm2
            selling_mkt = self.mm1
            buying_currency = self.mm2_currency
            selling_currency = self.mm1_currency
        else:
            raise Exception("Invalid trade type!")

        # check condition
        threshold_cond = spread_info.tradable_spread >= self.init_setting_dict[trade_type]["threshold"] >= 0
        min_coin_cond = spread_info.tradable_qty >= self.init_setting_dict["min_trading_coin"]

        # quit if conditions don't meet
        if not (threshold_cond and min_coin_cond):
            return None

        # get fee
        fee, should_fee = BasicAnalyzer.get_fee_consideration(buying_mkt.get_market_tag(), self.target_currency)
        # apply fee if any
        trading_amount = spread_info.tradable_qty + fee if should_fee else spread_info.tradable_qty

        # balance check
        krw_needed = spread_info.buy_price * self.init_setting_dict[trade_type]["factor"]
        coin_needed = trading_amount * self.init_setting_dict[trade_type]["factor"]
        has_enough_krw = RfabBacktester.has_enough_coin_checker(buying_mkt, "krw", krw_needed)
        has_enough_coin = RfabBacktester.has_enough_coin_checker(selling_mkt, self.target_currency, coin_needed)

        # if enough krw & coin balance
        if not (has_enough_krw and has_enough_coin):
            if not self.is_init_setting_opt:
                TradeInfoLogger.not_enough_balance_log_info(trade_type, spread_info)
            return None

        # make buy & sell order
        buy_order = buying_mkt.order_buy(buying_currency, spread_info.buy_price, trading_amount)
        sell_order = selling_mkt.order_sell(selling_currency, spread_info.sell_price, trading_amount)
        # subtract considered fee if there was one
        if should_fee:
            GlobalFeeAccumulator.sub_fee_consideration(buying_mkt.get_market_tag(), self.target_currency, fee)
        return Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta({}))

    @staticmethod
    def has_enough_coin_checker(market, coin_type: str, needed_amount: float):
        available_amount = market.balance.get_available_coin(coin_type.lower())
        if available_amount < needed_amount:
            return False
        else:
            return True

    def get_krw_total_balance(self):
        # log balance
        mm1_balance = self.mm1.get_balance()
        mm2_balance = self.mm2.get_balance()

        combined = BasicAnalyzer.combine_balance(mm1_balance, mm2_balance, (self.target_currency, "krw"))
        return combined["KRW"]["balance"]


class TradeInfoLogger:
    def __init__(self, trade_manager, target_currency):
        self.trade_manager = trade_manager
        self.target_currency = target_currency
        self.new_oppty_counter = 0
        self.rev_oppty_counter = 0

    def acc_oppty_counter(self, trade_type: str):
        attr_name = trade_type + "_oppty_counter"
        oppty_count = getattr(self, attr_name)
        setattr(self, attr_name, oppty_count + 1)

    def log_trade_info(self):
        trade_total = self.trade_manager.get_trade_count()
        trade_new = self.trade_manager.get_trade_count(TradeTag.NEW)
        trade_rev = self.trade_manager.get_trade_count(TradeTag.REV)

        try:
            logging.info("[STAT] total trades: %d, new trades: %d(%.2f%%), rev trades: %d(%.2f%%)" %
                         (trade_total, trade_new, trade_new / trade_total * 100,
                          trade_rev, trade_rev / trade_total * 100))
        except ZeroDivisionError:
            logging.info("[STAT] total trades: 0, new trades: 0, rev trades: 0")

    def log_oppty_info(self):
        # log opportunity counter
        logging.info("[STAT] total oppty: %d, new oppty: %d, rev oppty: %d" %
                     (self.new_oppty_counter + self.rev_oppty_counter,
                      self.new_oppty_counter, self.rev_oppty_counter))

    def log_combined_balance(self, mm1_balance, mm2_balance):
        # log combined balance
        combined = BasicAnalyzer.combine_balance(mm1_balance, mm2_balance, (self.target_currency, "krw"))
        for coin_name in combined.keys():
            balance = combined[coin_name]
            logging.info("[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                         (coin_name, balance["available"], balance["trade_in_use"], balance["balance"]))

    @staticmethod
    def execute_trade_log_info(trade: Trade, spread_info: SpreadInfo):
        trade_tag = trade.trade_tag.name.upper()
        trade_amount = trade.orders[0].order_amount
        logging.warning("[EXECUTE] %s ->"
                        "Trading INFOS: Spread in unit = %.2f, Traded Spread = %.2f, Traded_QTY = %.5f"
                        % (trade_tag, spread_info.spread_in_unit, spread_info.tradable_spread, trade_amount))

    @staticmethod
    def not_enough_balance_log_info(trade_tag, spread_info):
        logging.error("[EXECUTE] %s -> failed (not enough balance!) -> "
                      "Trading INFOS: Spread in unit = %.2f, Tradable Spread = %.2f, Tradable QTY= %.5f"
                      % (trade_tag.upper(), spread_info.spread_in_unit, spread_info.tradable_spread,
                         spread_info.tradable_qty))
