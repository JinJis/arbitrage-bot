import logging
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
        v_mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 45000, 0.1) if is_backtesting else None
        v_mm2 = VirtualMarketManager(Market.VIRTUAL_KB, 0.002, 45000, 0.1) if is_backtesting else None

        super().__init__(target_currency, target_interval_in_sec,
                         should_db_logging, is_backtesting, start_time, end_time, v_mm1, v_mm2)

        self.COIN_TRADING_UNIT = 0.1
        self.NEW_SPREAD_THRESHOLD = 0
        self.REV_SPREAD_THRESHOLD = 0
        self.SLIPPAGE_HEDGE = 0  # 향후에 거래량을 보고 결정할 parameter, 0.01로 거래한다는 가정하에 0.03으로 설정

        # init mongo related
        self.mm1_data_col = SharedMongoClient.get_coinone_db()[self.TARGET_CURRENCY + "_orderbook"]
        self.mm2_data_col = SharedMongoClient.get_korbit_db()[self.TARGET_CURRENCY + "_orderbook"]

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
        mm1_buy_amount_actual = self.mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)
        mm2_buy_amount_actual = self.mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT)
        mm1_buy_krw = mm1_buy_amount_actual * mm1_buy_price
        mm2_buy_krw = mm2_buy_amount_actual * mm2_buy_price

        # make decision
        if new_spread > self.NEW_SPREAD_THRESHOLD:
            self.new_oppty_counter += 1
            if (
                    self.mm1.has_enough_coin("krw", mm1_buy_krw)
                    and self.mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                    and mm1_buy_amount >= mm1_buy_amount_actual + self.SLIPPAGE_HEDGE
                    and mm2_sell_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
            ):
                logging.warning("[EXECUTE] New")
                buy_order = self.mm1.order_buy(self.mm1_currency, mm1_buy_price, mm1_buy_amount_actual)
                sell_order = self.mm2.order_sell(self.mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
                self.cur_trade = Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta({"sell_price": mm2_sell_price}))
                self.trade_manager.add_trade(self.cur_trade)
            else:
                logging.error("[EXECUTE] New -> failed (not enough balance!)")

        elif rev_spread > self.REV_SPREAD_THRESHOLD:
            self.rev_oppty_counter += 1
            if (
                    self.mm2.has_enough_coin("krw", mm2_buy_krw)
                    and self.mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                    and mm2_buy_amount >= mm2_buy_amount_actual + self.SLIPPAGE_HEDGE
                    and mm1_sell_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
            ):
                logging.warning("[EXECUTE] Reverse")
                buy_order = self.mm2.order_buy(self.mm2_currency, mm2_buy_price, mm2_buy_amount_actual)
                sell_order = self.mm1.order_sell(self.mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)
                self.cur_trade = Trade(TradeTag.REV, [buy_order, sell_order], TradeMeta({"sell_price": mm1_sell_price}))
                self.trade_manager.add_trade(self.cur_trade)
            else:
                logging.error("[EXECUTE] Reverse -> failed (not enough balance!)")

        else:
            logging.warning("[EXECUTE] No")

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
