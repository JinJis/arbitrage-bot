from trader.market.market import Market
import logging
from analyzer.analyzer import BasicAnalyzer
from analyzer.analyzer import ATSAnalyzer, SpreadInfo
from config.shared_mongo_client import SharedMongoClient
from trader.base_arb_bot import BaseArbBot
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from trader.trade_manager.trade_manager import TradeManager
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator


class RfabBacktester:
    TARGET_STRATEGY = ATSAnalyzer.actual_tradable_spread_strategy

    def __init__(self, mm1_balance_dict: dict, mm2_balance_dict: dict, initial_setting_dict: dict,
                 start_time: int, end_time: int, target_currency: str = None, is_init_setting_opt: bool = False):

        self.mm1 = VirtualMarketManager(mm1_balance_dict["mkt_tag"], mm1_balance_dict["market_fee"],
                                        mm1_balance_dict["krw_balance"],
                                        mm1_balance_dict["coin_balance"], target_currency)
        self.mm2 = VirtualMarketManager(mm2_balance_dict["mkt_tag"], mm2_balance_dict["market_fee"],
                                        mm2_balance_dict["krw_balance"],
                                        mm2_balance_dict["coin_balance"], target_currency)

        self.mm1_data_col = self.initialize_mongo(mm1_balance_dict, target_currency)
        self.mm2_data_col = self.initialize_mongo(mm2_balance_dict, target_currency)
        self.target_currency = target_currency
        self.init_setting_dict = initial_setting_dict
        self.start_time = start_time
        self.end_time = end_time
        self.new_oppty_counter = 0
        self.rev_oppty_counter = 0

        self.trade_manager = TradeManager(should_db_logging=True, is_backtesting=True)
        self.mm1_currency = self.mm1.get_market_currency(self.target_currency)
        self.mm2_currency = self.mm2.get_market_currency(self.target_currency)
        self.cur_trade = None
        self.is_init_setting_opt = is_init_setting_opt

    def run(self):
        # get cursor from mongodb
        mm1_data_cursor, mm2_data_cursor = \
            BaseArbBot.get_data_from_db(self.mm1_data_col, self.mm2_data_col,
                                        self.start_time, self.end_time)
        # loop through history data
        for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
            self.actual_trade_loop(mm1_data, mm2_data)

        # log backtesting result
        if not self.is_init_setting_opt:
            trade_logger = TradeInfoLogger(self.trade_manager, self.target_currency, self.new_oppty_counter,
                                           self.rev_oppty_counter)
            trade_logger.log_trade_info()
            trade_logger.log_oppty_info()
            trade_logger.log_combined_balance(self.mm1.balance, self.mm2.balance)

    def actual_trade_loop(self, mm1_data, mm2_data):
        # adjust orderbook for realistic backtesting
        self.mm1.apply_history_to_orderbook(mm1_data)
        self.mm2.apply_history_to_orderbook(mm2_data)

        spread_info = RfabBacktester.TARGET_STRATEGY(mm1_data, mm2_data, self.mm1.market_fee, self.mm2.market_fee,
                                                     self.init_setting_dict["max_trading_coin"])

        # Dictionary that possess spread information that will be used in trading algorithms
        new_spread_info = spread_info["new"]
        rev_spread_info = spread_info["rev"]

        # make decision
        # NEW
        if new_spread_info.spread_in_unit > 0:
            # increase oppty count
            self.new_oppty_counter += 1

            # decide whether to trade
            buy_order, sell_order = self.trade_logic(new_spread_info, self.mm1, self.mm2, self.target_currency,
                                                     self.mm1_currency, self.mm2_currency, self.init_setting_dict,
                                                     trade_tag="new")
            # if there was any execution, add trade
            if buy_order and sell_order:
                self.cur_trade = Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta({}))
                self.trade_manager.add_trade(self.cur_trade)

        # REVERSE
        if rev_spread_info.spread_in_unit > 0:
            self.rev_oppty_counter += 1
            # decide whether to trade
            buy_order, sell_order = self.trade_logic(rev_spread_info, self.mm2, self.mm1, self.target_currency,
                                                     self.mm2_currency,
                                                     self.mm1_currency, self.init_setting_dict, trade_tag="rev")
            # if there was any execution, add trade
            if buy_order and sell_order:
                self.cur_trade = Trade(TradeTag.REV, [buy_order, sell_order], TradeMeta({}))
                self.trade_manager.add_trade(self.cur_trade)

        # if there was any trade
        if self.cur_trade is not None:
            # update & log individual balance
            self.mm1.update_balance()
            self.mm2.update_balance()

    def execute_trade(self, buy_order, sell_order):
        self.cur_trade = Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta({}))
        self.trade_manager.add_trade(self.cur_trade)

    @staticmethod
    def trade_logic(spread_info: SpreadInfo, buying_mkt, selling_mkt, target_currency, buying_currency,
                    selling_currency, init_setting_dict: dict, trade_tag: str = "new" or "rev",
                    is_init_setting_opt: bool = False):
        # check condition
        threshold_cond = spread_info.tradable_spread >= init_setting_dict[trade_tag]["threshold"] >= 0
        min_coin_cond = spread_info.tradable_qty >= init_setting_dict["min_trading_coin"]

        if threshold_cond and min_coin_cond:
            # get fee
            fee, should_fee = BasicAnalyzer.get_fee_consideration(buying_mkt.get_market_tag(), target_currency)
            # apply fee if any
            trading_amount = spread_info.tradable_qty + fee if should_fee else spread_info.tradable_qty

            # balance check
            has_enough_krw = buying_mkt.has_enough_coin("krw", spread_info.buy_price * init_setting_dict[trade_tag][
                "factor"])
            has_enough_coin = selling_mkt.has_enough_coin(target_currency,
                                                          trading_amount * init_setting_dict[trade_tag]["factor"])

            if has_enough_krw and has_enough_coin:
                # subtract considered fee if there was one
                if should_fee:
                    GlobalFeeAccumulator.sub_fee_consideration(buying_mkt.get_market_tag(), target_currency, fee)

                if not is_init_setting_opt:
                    # log executed trade info
                    TradeInfoLogger.execute_trade_log_info(trade_tag, spread_info, trading_amount)

                # excute trade
                buy_order = buying_mkt.order_buy(buying_currency, spread_info.buy_price, trading_amount)
                sell_order = selling_mkt.order_sell(selling_currency, spread_info.sell_price, trading_amount)
                return buy_order, sell_order
            else:
                if not is_init_setting_opt:
                    # log failed trade (not enough mkt amount)
                    TradeInfoLogger.not_enough_mkt_qty_log_info(trade_tag, spread_info)
                return None, None
        return None, None

    @staticmethod
    def initialize_mongo(mm_dict: dict, target_currency: str):
        method_name = {
            Market.VIRTUAL_CO: "get_coinone_db",
            Market.VIRTUAL_KB: "get_korbit_db",
            Market.VIRTUAL_GP: "get_gopax_db"
        }[mm_dict["mkt_tag"]]
        return getattr(SharedMongoClient, method_name)()[target_currency + "_orderbook"]


class TradeInfoLogger:
    def __init__(self, trade_manager, target_currency, new_oppty_counter, rev_oppty_counter):

        self.trade_manager = trade_manager
        self.target_currency = target_currency
        self.new_oppty_counter = new_oppty_counter
        self.rev_oppty_counter = rev_oppty_counter

    def log_trade_info(self):
        trade_total = self.trade_manager.get_trade_count()
        trade_new = self.trade_manager.get_trade_count(TradeTag.NEW)
        trade_rev = self.trade_manager.get_trade_count(TradeTag.REV)

        try:
            logging.info("\n")
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
    def execute_trade_log_info(trade_tag, spread_info, trading_amount):
        logging.warning("[EXECUTE] %s ->"
                        "Trading INFOS: Spread in unit = %.2f, Traded Spread = %.2f, Traded_QTY = %.5f"
                        % (trade_tag.upper(), spread_info.spread_in_unit, spread_info.tradable_spread,
                           trading_amount))

    @staticmethod
    def not_enough_mkt_qty_log_info(trade_tag, spread_info):
        logging.error("[EXECUTE] %s -> failed (not enough balance!) ->"
                      "Trading INFOS: Spread in unit = %.2f, Tradable Spread = %.2f, Tradable QTY= %.5f"
                      % (trade_tag.upper(), spread_info.spread_in_unit, spread_info.tradable_spread,
                         spread_info.tradable_qty))
