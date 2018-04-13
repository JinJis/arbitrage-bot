import logging
from trader.market.order import Order
from config.global_conf import Global
from analyzer.analyzer import Analyzer
from trader.market.market import Market
from trader.base_arb_bot import BaseArbBot
from config.shared_mongo_client import SharedMongoClient
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from trader.trade_manager.order_watcher_stats import OrderWatcherStats

"""
!!! IMPORTANT NOTE !!!

[NEW Spread] => buy in mm1, sell in mm2
[REV Spread] => buy in mm2, sell in mm1

MODIFY config.global_conf > COIN_FILTER_FOR_BALANCE for balance creation!
"""


class RiskFreeArbBot(BaseArbBot):
    TARGET_STRATEGY = Analyzer.buy_sell_strategy_1

    def __init__(self,
                 target_currency: str = "eth", target_interval_in_sec: int = 5,
                 should_db_logging: bool = True,
                 is_backtesting: bool = False, start_time: int = None, end_time: int = None):

        # init virtual mm when backtesting
        v_mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 75000, 0.05) if is_backtesting else None
        v_mm2 = VirtualMarketManager(Market.VIRTUAL_KB, 0.002, 25000, 0.25) if is_backtesting else None

        super().__init__(target_currency, target_interval_in_sec,
                         should_db_logging, is_backtesting, start_time, end_time, v_mm1, v_mm2)

        self.COIN_TRADING_UNIT = 0.02
        self.NEW_SPREAD_THRESHOLD = 0
        self.REV_SPREAD_THRESHOLD = 0
        self.MARGIN_KRW_THRESHOLD = 500
        self.SLIPPAGE_HEDGE = 0  # 향후에 거래량을 보고 결정할 parameter, 0.01로 거래한다는 가정하에 0.03으로 설정

        # init mongo related
        self.mm1_data_col = SharedMongoClient.get_coinone_db()[self.TARGET_CURRENCY + "_orderbook"]
        self.mm2_data_col = SharedMongoClient.get_korbit_db()[self.TARGET_CURRENCY + "_orderbook"]

        # if buy +1, if sell -1
        self.mm1_buy_sell_diff_count = 0
        self.mm2_buy_sell_diff_count = 0

        self.mm1_buy_orders = list()
        self.mm1_sell_orders = list()
        self.mm2_buy_orders = list()
        self.mm2_sell_orders = list()

        self.mm1_buy_manual_flag = False
        self.mm1_sell_manual_flag = False
        self.mm2_buy_manual_flag = False
        self.mm2_sell_manual_flag = False

        self.new_manual_flag = False
        self.rev_manual_flag = False

        self.new_manual_count = 0
        self.rev_manual_count = 0

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
            logging.info("%s, %s, %s, %s" %
                         (self.mm1_buy_manual_flag, self.mm1_sell_manual_flag,
                          self.mm2_buy_manual_flag, self.mm2_sell_manual_flag))
            logging.info("manual new: %d, manual rev: %d" % (self.new_manual_count, self.rev_manual_count))

    def actual_trade_loop(self, mm1_data=None, mm2_data=None):
        # get current spread
        if not self.is_backtesting:
            mm1_orderbook = self.mm1.get_orderbook(self.mm1_currency)
            mm2_orderbook = self.mm2.get_orderbook(self.mm2_currency)
            new_spread, rev_spread, \
            mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price, \
            mm1_buy_amount, mm1_sell_amount, mm2_buy_amount, mm2_sell_amount = \
                RiskFreeArbBot.TARGET_STRATEGY(mm1_orderbook, mm2_orderbook, self.mm1.market_fee, self.mm2.market_fee)
        else:
            new_spread, rev_spread, \
            mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price, \
            mm1_buy_amount, mm1_sell_amount, mm2_buy_amount, mm2_sell_amount = \
                RiskFreeArbBot.TARGET_STRATEGY(mm1_data, mm2_data, self.mm1.market_fee, self.mm2.market_fee)

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
                    logging.warning("[EXECUTE] New")
                    buy_order = self.mm1.order_buy(self.mm1_currency, mm1_buy_price, self.mm1_buy_coin_trading_unit)
                    sell_order = self.mm2.order_sell(self.mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
                    self.cur_trade = Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta(None))
                    self.trade_manager.add_trade(self.cur_trade)

                    # record orders
                    self.mm1_buy_orders.append(buy_order)
                    self.mm2_sell_orders.append(sell_order)
                    self.mm1_buy_sell_diff_count += 1
                    self.mm2_buy_sell_diff_count -= 1
                else:
                    logging.error("[EXECUTE] New -> failed (not enough available amount in market!)")
            else:
                logging.error("[EXECUTE] New -> failed (not enough balance!)")

        elif rev_spread > self.REV_SPREAD_THRESHOLD:
            self.rev_oppty_counter += 1
            if (
                    self.mm2.has_enough_coin("krw", mm2_buy_krw)
                    and self.mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
            ):
                if (
                        mm2_buy_amount >= self.mm2_buy_coin_trading_unit + self.SLIPPAGE_HEDGE
                        and mm1_sell_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
                ):
                    logging.warning("[EXECUTE] Reverse")
                    buy_order = self.mm2.order_buy(self.mm2_currency, mm2_buy_price, self.mm2_buy_coin_trading_unit)
                    sell_order = self.mm1.order_sell(self.mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)
                    self.cur_trade = Trade(TradeTag.REV, [buy_order, sell_order], TradeMeta(None))
                    self.trade_manager.add_trade(self.cur_trade)

                    # record orders
                    self.mm2_buy_orders.append(buy_order)
                    self.mm1_sell_orders.append(sell_order)
                    self.mm2_buy_sell_diff_count += 1
                    self.mm1_buy_sell_diff_count -= 1
                else:
                    logging.error("[EXECUTE] Reverse -> failed (not enough available amount in market!)")
            else:
                logging.error("[EXECUTE] Reverse -> failed (not enough balance!)")

        else:
            logging.info("[EXECUTE] No")

        # if there's more buy than sell in mm1 (new > rev)
        if (
                (self.mm1_buy_sell_diff_count > 0 or self.rev_manual_flag)
                and not self.mm1_sell_manual_flag
                and not self.new_manual_flag
        ):
            for mm1_buy_order in self.mm1_buy_orders:
                # calc spread with current sell price
                profit = Analyzer.calc_spread(mm1_buy_order.price, self.mm1.market_fee,
                                              mm1_sell_price, self.mm1.market_fee)
                if profit > self.MARGIN_KRW_THRESHOLD:
                    # mm1 sell
                    self.mm1.order_sell(self.mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)
                    self.mm1_buy_orders.remove(mm1_buy_order)
                    self.mm1_buy_sell_diff_count -= 1

                    # if mm2 buy was done before
                    if self.mm2_buy_manual_flag:
                        self.mm2_buy_manual_flag = False
                        self.rev_manual_count += 1
                        self.rev_manual_flag = False
                        logging.warning("Manual REV position done!")
                    else:
                        self.mm1_sell_manual_flag = True
                        self.rev_manual_flag = True
                        logging.warning("Manual REV position start!")
                    break

        # if there's more sell than buy in mm1 (rev > new)
        elif (
                (self.mm1_buy_sell_diff_count < 0 or self.new_manual_flag)
                and not self.mm1_buy_manual_flag
                and not self.rev_manual_flag
        ):
            for mm1_sell_order in self.mm1_sell_orders:
                # calc spread with current buy price
                profit = Analyzer.calc_spread(mm1_buy_price, self.mm1.market_fee,
                                              mm1_sell_order.price, self.mm1.market_fee)
                if profit > self.MARGIN_KRW_THRESHOLD:
                    # mm1 buy
                    self.mm1.order_buy(self.mm1_currency, mm1_buy_price, self.mm1_buy_coin_trading_unit)
                    self.mm1_sell_orders.remove(mm1_sell_order)
                    self.mm1_buy_sell_diff_count += 1

                    # if mm2 sell was done before
                    if self.mm2_sell_manual_flag:
                        self.mm2_sell_manual_flag = False
                        self.new_manual_count += 1
                        self.new_manual_flag = False
                        logging.warning("Manual NEW position done!")
                    else:
                        self.mm1_buy_manual_flag = True
                        self.new_manual_flag = True
                        logging.warning("Manual NEW position start!")
                    break

        # if there's more buy than sell in mm2 (rev > new)
        if (
                (self.mm2_buy_sell_diff_count > 0 or self.new_manual_flag)
                and not self.mm2_sell_manual_flag
                and not self.rev_manual_flag
        ):
            for mm2_buy_order in self.mm2_buy_orders:
                # calc spread with current sell price
                profit = Analyzer.calc_spread(mm2_buy_order.price, self.mm2.market_fee,
                                              mm2_sell_price, self.mm2.market_fee)
                if profit > self.MARGIN_KRW_THRESHOLD:
                    # mm2 sell
                    self.mm2.order_sell(self.mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
                    self.mm2_buy_orders.remove(mm2_buy_order)
                    self.mm2_buy_sell_diff_count -= 1

                    # if mm1 buy was done before
                    if self.mm1_buy_manual_flag:
                        self.mm1_buy_manual_flag = False
                        self.new_manual_count += 1
                        logging.warning("Manual NEW position done!")
                    else:
                        self.mm2_sell_manual_flag = True
                        logging.warning("Manual NEW position start!")
                    break

        # if there's more sell than buy in mm2 (new > rev)
        elif (
                (self.mm2_buy_sell_diff_count < 0 or self.rev_manual_flag)
                and not self.mm2_buy_manual_flag
                and not self.new_manual_flag
        ):
            for mm2_sell_order in self.mm2_sell_orders:
                # calc spread with current buy price
                profit = Analyzer.calc_spread(mm2_buy_price, self.mm2.market_fee,
                                              mm2_sell_order.price, self.mm2.market_fee)
                if profit > self.MARGIN_KRW_THRESHOLD:
                    # mm2 buy
                    self.mm2.order_buy(self.mm2_currency, mm2_buy_price, self.mm2_buy_coin_trading_unit)
                    self.mm2_sell_orders.remove(mm2_sell_order)
                    self.mm2_buy_sell_diff_count += 1

                    # if mm1 sell was done before
                    if self.mm1_sell_manual_flag:
                        self.mm1_sell_manual_flag = False
                        self.rev_manual_count += 1
                        logging.warning("Manual REV position done!")
                    else:
                        self.mm2_buy_manual_flag = True
                        logging.warning("Manual REV position start!")
                    break

        # if there was any trade
        if self.cur_trade is not None:
            # update & log individual balance
            self.mm1.update_balance()
            self.mm2.update_balance()
            logging.info(self.mm1.get_balance())
            logging.info(self.mm2.get_balance())

            # log combined balance
            combined = Analyzer.combine_balance(self.mm1.get_balance(), self.mm2.get_balance())
            for coin_name in combined.keys():
                balance = combined[coin_name]
                logging.info("[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                             (coin_name, balance["available"], balance["trade_in_use"], balance["balance"]))
