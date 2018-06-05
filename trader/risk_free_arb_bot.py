import logging
from config.global_conf import Global
from analyzer.analyzer import Analyzer
from trader.market.market import Market
from trader.base_arb_bot import BaseArbBot
from config.shared_mongo_client import SharedMongoClient
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from trader.trade_manager.order_watcher_stats import OrderWatcherStats
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.gopax_market_manager import GopaxMarketManager
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator

"""
!!! IMPORTANT NOTE !!!

[NEW Spread] => buy in mm1, sell in mm2
[REV Spread] => buy in mm2, sell in mm1

MODIFY config.global_conf > COIN_FILTER_FOR_BALANCE for balance creation!
"""


class RiskFreeArbBot1(BaseArbBot):
    TARGET_STRATEGY = Analyzer.buy_sell_strategy_1

    def __init__(self,
                 target_currency: str, target_interval_in_sec: int = 5,
                 should_db_logging: bool = True,
                 is_backtesting: bool = False, start_time: int = None, end_time: int = None):

        # init virtual mm when backtesting
        v_mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 4000000, 0.04, target_currency)
        v_mm2 = VirtualMarketManager(Market.VIRTUAL_GP, 0.00075, 400000, 0.4, target_currency)

        super().__init__(v_mm1, v_mm2, target_currency, target_interval_in_sec, should_db_logging,
                         is_backtesting, start_time, end_time)

        self.COIN_TRADING_UNIT = 0.0005
        self.NEW_SPREAD_THRESHOLD = 0
        self.REV_SPREAD_THRESHOLD = 0
        self.MARGIN_KRW_THRESHOLD = 0
        self.SLIPPAGE_HEDGE = 0  # 향후에 거래량을 보고 결정할 parameter, 0.01로 거래한다는 가정하에 0.03으로 설정
        self.REV_FACTOR = 1

        # init mongo related
        self.mm1_data_col = SharedMongoClient.get_coinone_db()[self.TARGET_CURRENCY + "_orderbook"]
        self.mm2_data_col = SharedMongoClient.get_gopax_db()[self.TARGET_CURRENCY + "_orderbook"]

        self.mm1_buy_coin_trading_unit = self.mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)
        self.mm2_buy_coin_trading_unit = self.mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)

    def run(self):
        # log initial balance
        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(self.mm1.get_balance())
        logging.info(self.mm2.get_balance())

        # if not backtesting
        if not self.is_backtesting:
            while True:
                try:
                    self.execute_trade_loop()
                except Exception as e:
                    Global.send_to_slack_channel("Something happened to StatArbBot! Now it's dying from ... %s" % e)
                    # stop order watcher stats thread
                    OrderWatcherStats.instance().tear_down()
                    raise e
        # if backtesting
        else:
            # collect historical data from db
            logging.info("Collecting historical data, please wait...")
            mm1_data_cursor, mm2_data_cursor = \
                self.get_data_from_db(self.mm1_data_col, self.mm2_data_col,
                                      self.start_time, self.end_time)

            # loop through history data
            for mm1_data, mm2_data in zip(mm1_data_cursor, mm2_data_cursor):
                self.execute_trade_loop(mm1_data, mm2_data)

            # log backtesting result
            self.log_common_stat(log_level=logging.CRITICAL)

    def actual_trade_loop(self, mm1_data=None, mm2_data=None):
        if not self.is_backtesting:
            mm1_data = self.mm1.get_orderbook(self.mm1_currency)
            mm2_data = self.mm2.get_orderbook(self.mm2_currency)
        else:
            self.mm1.apply_history_to_orderbook(mm1_data)
            self.mm2.apply_history_to_orderbook(mm2_data)

        # get current spread
        new_spread, rev_spread, \
        mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price, \
        mm1_buy_amount, mm1_sell_amount, mm2_buy_amount, mm2_sell_amount = \
            RiskFreeArbBot1.TARGET_STRATEGY(mm1_data, mm2_data, self.mm1.market_fee, self.mm2.market_fee)

        # log stat
        logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (self.mm1.get_market_name(),
                                                                   mm1_buy_price, mm1_sell_price))
        logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (self.mm2.get_market_name(),
                                                                   mm2_buy_price, mm2_sell_price))
        logging.info("[STAT] new_spread: %d, rev_spread: %d" % (new_spread, rev_spread))

        # calculate needed krw
        mm1_buy_krw = self.mm1_buy_coin_trading_unit * mm1_buy_price
        mm2_buy_krw = self.mm2_buy_coin_trading_unit * mm2_buy_price

        # make decision
        if new_spread > self.NEW_SPREAD_THRESHOLD:
            self.new_oppty_counter += 1
            if (
                        self.mm1.has_enough_coin("krw", mm1_buy_krw)
                    and self.mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
            ):
                if (
                                mm1_buy_amount >= self.mm1_buy_coin_trading_unit + self.SLIPPAGE_HEDGE
                        and mm2_sell_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
                ):
                    logging.warning("[EXECUTE] New <---- Spread = %.2f / "
                                    "Market amount [mm1 = %.4f, mm2= %.4f]"
                                    % (new_spread, mm1_buy_amount, mm2_sell_amount))
                    buy_order = self.mm1.order_buy(self.mm1_currency, mm1_buy_price, self.mm1_buy_coin_trading_unit)
                    sell_order = self.mm2.order_sell(self.mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
                    self.cur_trade = Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta({}))
                    self.trade_manager.add_trade(self.cur_trade)
                else:
                    logging.error("[EXECUTE] New -> failed "
                                  "(not enough available amount in market!) "
                                  "<-- Market amount [mm1 = %.4f, mm2= %.4f]" % (mm1_buy_amount, mm2_sell_amount))
            else:
                logging.error("[EXECUTE] New -> failed (not enough balance!)")

        elif rev_spread > self.REV_SPREAD_THRESHOLD:
            self.rev_oppty_counter += 1
            if (
                        self.mm2.has_enough_coin("krw", mm2_buy_krw * self.REV_FACTOR)
                    and self.mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT * self.REV_FACTOR)
            ):
                if (
                                mm2_buy_amount >= self.mm2_buy_coin_trading_unit * self.REV_FACTOR + self.SLIPPAGE_HEDGE
                        and mm1_sell_amount >= self.COIN_TRADING_UNIT * self.REV_FACTOR + self.SLIPPAGE_HEDGE
                ):
                    logging.warning("[EXECUTE] Reverse <---- Spread = %.2f / "
                                    "Market amount [mm1 = %.4f, mm2= %.4f]"
                                    % (rev_spread, mm1_sell_amount, mm2_buy_amount))
                    buy_order = self.mm2.order_buy(self.mm2_currency, mm2_buy_price,
                                                   self.mm2_buy_coin_trading_unit * self.REV_FACTOR)
                    sell_order = self.mm1.order_sell(self.mm1_currency, mm1_sell_price,
                                                     self.COIN_TRADING_UNIT * self.REV_FACTOR)
                    self.cur_trade = Trade(TradeTag.REV, [buy_order, sell_order], TradeMeta({}))
                    self.trade_manager.add_trade(self.cur_trade)
                else:
                    logging.error("[EXECUTE] Reverse -> failed "
                                  "(not enough available amount in market!) "
                                  "<-- Market amount [mm1 = %.4f, mm2= %.4f]" % (mm1_sell_amount, mm2_buy_amount))
            else:
                logging.error("[EXECUTE] Reverse -> failed (not enough balance!)")

        else:
            logging.info("[EXECUTE] No")

        # if there was any trade
        if self.cur_trade is not None:
            # update & log individual balance
            self.mm1.update_balance()
            self.mm2.update_balance()
            logging.info(self.mm1.get_balance())
            logging.info(self.mm2.get_balance())

            # log combined balance
            combined = Analyzer.combine_balance(self.mm1.get_balance(), self.mm2.get_balance(),
                                                (self.TARGET_CURRENCY, "krw"))
            for coin_name in combined.keys():
                balance = combined[coin_name]
                logging.info("[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                             (coin_name, balance["available"], balance["trade_in_use"], balance["balance"]))


"""
<< Explanation about Risk Free Arbitrage Bot2 >>

* Backgrounds 
    RFAB1 (Risk Free Arbitrage Bot 1) deals soley with ma[0] and mb[0] of mm1 and mm2 accordingly, restricing 
    not too small trading opportunities because of limited quantity of price available at those moments.
    
* How?
    RFAB2 decides of which combination each trading opportunity would give the best performance by evaluating
    all the variables needed for the profit function (of course, always greater or equal to 0) like price of asks 
    and bids, quantity of asks and bids accordingly.
"""


class RiskFreeArbBot2(BaseArbBot):
    TARGET_STRATEGY = Analyzer.optimized_tradable_spread_strategy
    IS_DATA_EXIST = False

    def __init__(self,
                 target_currency: str, target_interval_in_sec: int = 5,
                 should_db_logging: bool = True,
                 is_backtesting: bool = False, is_init_setting_opt: bool = False,
                 start_time: int = None, end_time: int = None):

        if not is_backtesting:
            mm1 = CoinoneMarketManager()
            mm2 = GopaxMarketManager()
        else:
            mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 5000000, 0.5, target_currency)
            mm2 = VirtualMarketManager(Market.VIRTUAL_GP, 0.00075, 500000, 5, target_currency)

        super().__init__(mm1, mm2, target_currency, target_interval_in_sec, should_db_logging,
                         is_backtesting, is_init_setting_opt, start_time, end_time)

        self.MAX_COIN_TRADING_UNIT = 0.005
        self.MIN_COIN_TRADING_UNIT = 0
        self.MAX_OB_INDEX_NUM = 2
        self.NEW_SPREAD_THRESHOLD = 0
        self.REV_SPREAD_THRESHOLD = 0
        self.REV_FACTOR = 1.5

        self.mm1_data_cur = None
        self.mm2_data_cur = None
        self.trade_new = 0
        self.trade_rev = 0

        # init mongo related
        self.mm1_data_col = SharedMongoClient.get_coinone_db()[self.TARGET_CURRENCY + "_orderbook"]
        self.mm2_data_col = SharedMongoClient.get_gopax_db()[self.TARGET_CURRENCY + "_orderbook"]

    def run(self):
        # log initial balance
        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(self.mm1.get_balance())
        logging.info(self.mm2.get_balance())

        # if not backtesting
        if not self.is_backtesting:
            while True:
                try:
                    self.execute_trade_loop()
                except Exception as e:
                    Global.send_to_slack_channel("Something happened to StatArbBot! Now it's dying from ... %s" % e)
                    # stop order watcher stats thread
                    OrderWatcherStats.instance().tear_down()
                    raise e
        # if backtesting
        else:
            # collect historical data from db
            # If there is no data
            if not RiskFreeArbBot2.IS_DATA_EXIST:
                RiskFreeArbBot2.mm1_data_cur, RiskFreeArbBot2.mm2_data_cur = self.get_data_from_db(
                    self.mm1_data_col, self.mm2_data_col, self.start_time, self.end_time)
                RiskFreeArbBot2.IS_DATA_EXIST = True

            self.mm1_data_cur = RiskFreeArbBot2.mm1_data_cur.clone()
            self.mm2_data_cur = RiskFreeArbBot2.mm2_data_cur.clone()

            # loop through historical data
            for mm1_data, mm2_data in zip(self.mm1_data_cur, self.mm2_data_cur):
                self.execute_trade_loop(mm1_data, mm2_data)

            # log backtesting result
            if not self.is_init_setting_opt:
                self.log_common_stat(log_level=logging.CRITICAL)
            # when initial setting opt
            else:
                self.get_krw_total_balance()
                self.trade_new = self.trade_manager.get_trade_count(TradeTag.NEW)
                self.trade_rev = self.trade_manager.get_trade_count(TradeTag.REV)

    def actual_trade_loop(self, mm1_data=None, mm2_data=None):
        if not self.is_backtesting:
            mm1_data = self.mm1.get_orderbook(self.mm1_currency)
            mm2_data = self.mm2.get_orderbook(self.mm2_currency)
        else:
            self.mm1.apply_history_to_orderbook(mm1_data)
            self.mm2.apply_history_to_orderbook(mm2_data)

        # get optimized spread infos by using OTS strategy
        (new_spread_in_unit, rev_spread_in_unit, opt_new_spread, opt_rev_spread,
         new_buy_price, new_buy_idx, new_sell_price, new_sell_idx, new_trading_amount,
         rev_buy_price, rev_buy_idx, rev_sell_price, rev_sell_idx, rev_trading_amount,
         new_avail_mm1_qty, new_avail_mm2_qty, rev_avail_mm1_qty, rev_avail_mm2_qty) = \
            RiskFreeArbBot2.TARGET_STRATEGY(mm1_data, mm2_data, self.mm1.market_fee, self.mm2.market_fee,
                                            self.MAX_OB_INDEX_NUM, self.MAX_COIN_TRADING_UNIT)

        # log stat
        logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (self.mm1.get_market_name(),
                                                                   new_buy_price, new_sell_price))
        logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (self.mm2.get_market_name(),
                                                                   rev_buy_price, rev_sell_price))
        logging.info("[STAT] new_spread: %d, rev_spread: %d" % (opt_new_spread, opt_rev_spread))

        # calculate needed krw
        mm1_buy_krw = new_trading_amount / (1 - self.mm1.market_fee) * new_buy_price
        mm2_buy_krw = rev_trading_amount / (1 - self.mm2.market_fee) * rev_buy_price

        # make decision
        if opt_new_spread >= self.NEW_SPREAD_THRESHOLD and not opt_new_spread == 0 \
                and new_trading_amount >= self.MIN_COIN_TRADING_UNIT:
            self.new_oppty_counter += 1
            fee, should_fee = Analyzer.get_fee_consideration(self.mm1.get_market_tag(), self.TARGET_CURRENCY)
            new_trading_amount = new_trading_amount + fee if should_fee else new_trading_amount
            if (
                        self.mm1.has_enough_coin("krw", mm1_buy_krw)
                    and self.mm2.has_enough_coin(self.TARGET_CURRENCY, new_trading_amount)
            ):
                logging.warning("[EXECUTE] New ->"
                                "Trading INFOS: Spread in unit = %.2f, BUY_index = %d, "
                                "SELL_index = %d, T_Spread = %.2f, T_QTY = %.5f, mkt_QTY = [mm1: %.5f, mm2: %.5f] "
                                % (new_spread_in_unit, new_buy_idx, new_sell_idx,
                                   opt_new_spread, new_trading_amount, new_avail_mm1_qty, new_avail_mm2_qty))
                buy_order = self.mm1.order_buy(self.mm1_currency, new_buy_price, new_trading_amount)
                sell_order = self.mm2.order_sell(self.mm2_currency, new_sell_price, new_trading_amount)
                self.cur_trade = Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta({}))
                self.trade_manager.add_trade(self.cur_trade)

                # subtract considered fee if there was one
                if should_fee:
                    GlobalFeeAccumulator.sub_fee_consideration(self.mm1.get_market_tag(), self.TARGET_CURRENCY, fee)

            else:
                logging.error("[EXECUTE] New -> failed (not enough balance!) ->"
                              "Trading INFOS: Spread in unit = %.2f, Psb Traded Spread = %.2f, MKT avail QTY = %.5f"
                              % (new_spread_in_unit, opt_new_spread, new_trading_amount))

        elif opt_rev_spread >= self.REV_SPREAD_THRESHOLD and not opt_rev_spread == 0 \
                and rev_trading_amount >= self.MIN_COIN_TRADING_UNIT:
            self.rev_oppty_counter += 1
            fee, should_fee = Analyzer.get_fee_consideration(self.mm2.get_market_tag(), self.TARGET_CURRENCY)
            rev_trading_amount = rev_trading_amount + fee if should_fee else rev_trading_amount
            if (
                        self.mm2.has_enough_coin("krw", mm2_buy_krw * self.REV_FACTOR)
                    and self.mm1.has_enough_coin(self.TARGET_CURRENCY, rev_trading_amount * self.REV_FACTOR)
            ):
                logging.warning("[EXECUTE] Reverse ->"
                                "Trading INFOS: Spread = %.2f, BUY_index = %d, "
                                "SELL_index = %d, T_Spread = %.2f, T_QTY = %.5f, mkt_QTY = [mm1: %.5f, mm2: %.5f]"
                                % (rev_spread_in_unit, rev_buy_idx, rev_sell_idx,
                                   opt_rev_spread, rev_trading_amount, rev_avail_mm1_qty, rev_avail_mm2_qty))
                buy_order = self.mm2.order_buy(self.mm2_currency, rev_buy_price, rev_trading_amount)
                sell_order = self.mm1.order_sell(self.mm1_currency, rev_sell_price, rev_trading_amount)
                self.cur_trade = Trade(TradeTag.REV, [buy_order, sell_order], TradeMeta({}))
                self.trade_manager.add_trade(self.cur_trade)

                # subtract considered fee if there was one
                if should_fee:
                    GlobalFeeAccumulator.sub_fee_consideration(self.mm2.get_market_tag(), self.TARGET_CURRENCY, fee)
            else:
                logging.error("[EXECUTE] Reverse -> failed (not enough balance!) ->"
                              "Trading INFOS: Spread in unit = %.2f, Psb Traded Spread = %.2f, MKT avail QTY = %.5f"
                              % (rev_spread_in_unit, opt_rev_spread, rev_trading_amount))

        else:
            logging.info("[EXECUTE] No")

        # if there was any trade

        if self.cur_trade is not None:
            # update & log individual balance
            self.mm1.update_balance()
            self.mm2.update_balance()
            logging.info(self.mm1.get_balance())
            logging.info(self.mm2.get_balance())

            # log combined balance
            combined = Analyzer.combine_balance(self.mm1.get_balance(), self.mm2.get_balance(),
                                                (self.TARGET_CURRENCY, "krw"))
            for coin_name in combined.keys():
                balance = combined[coin_name]
                logging.info("[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                             (coin_name, balance["available"], balance["trade_in_use"], balance["balance"]))

        if not self.is_backtesting:
            self.log_order_watcher_stats()
