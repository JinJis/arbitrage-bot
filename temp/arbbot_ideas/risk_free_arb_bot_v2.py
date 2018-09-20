import logging
from config.global_conf import Global
from analyzer.trade_analyzer import ATSAnalyzer
from trader.base_arb_bot import BaseArbBot
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.market_manager.market_manager import MarketManager
from temp.arbbot_ideas.trade_streamer import TradeStreamer
from trader.trade_manager.order_watcher_stats import OrderWatcherStats

"""
!!! IMPORTANT NOTE !!!

[NEW Spread] => buy in mm1, sell in mm2
[REV Spread] => buy in mm2, sell in mm1

MODIFY config.global_conf > COIN_FILTER_FOR_BALANCE for balance creation!
"""


class RiskFreeArbBotV2(BaseArbBot, TradeStreamer):
    TARGET_STRATEGY = ATSAnalyzer.actual_tradable_spread_strategy

    def __init__(self,
                 target_currency: str, mm1: MarketManager, mm2: MarketManager, target_interval_in_sec: int = 5,
                 should_db_logging: bool = True, is_backtesting: bool = False):

        self.mm1 = mm1
        self.mm2 = mm2

        super().__init__(self.mm1, self.mm2, target_currency, target_interval_in_sec, should_db_logging, is_backtesting)

        self.mm1_buy_orders = list()
        self.mm1_sell_orders = list()
        self.mm2_buy_orders = list()
        self.mm2_sell_orders = list()

    def run(self, initial_setting_dict: dict):
        # log initial balance
        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(self.mm1.get_balance())
        logging.info(self.mm2.get_balance())

        # launch RFAB Trade Streamer
        while True:
            try:
                self.execute_trade_loop()
            except Exception as e:
                Global.send_to_slack_channel("Something happened to RFAB! Now it's dying from ... %s" % e)
                # stop order watcher stats thread
                OrderWatcherStats.instance().tear_down()
                raise e

    def actual_trade_loop(self, mm1_data=None, mm2_data=None):
        # get current spread
        mm1_orderbook = self.mm1.get_orderbook(self.mm1_currency)
        mm2_orderbook = self.mm2.get_orderbook(self.mm2_currency)
        self.TARGET_STRATEGY(mm1_orderbook, mm2_orderbook, self.mm1.market_fee, self.mm2.market_fee, )

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
                    and self.mm2.has_enough_coin(self.target_currency, self.COIN_TRADING_UNIT)
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
                    and self.mm1.has_enough_coin(self.target_currency, self.COIN_TRADING_UNIT)
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

        # if there was any trade
        if self.cur_trade is not None:
            # update & log individual balance
            self.mm1.update_balance()
            self.mm2.update_balance()
            logging.info(self.mm1.get_balance())
            logging.info(self.mm2.get_balance())

            # log combined balance
            combined = Analyzer.combine_balance(self.mm1.get_balance(), self.mm2.get_balance(),
                                                (self.target_currency, "krw"))
            for coin_name in combined.keys():
                balance = combined[coin_name]
                logging.info("[TOTAL %s]: available - %.4f, trade_in_use - %.4f, balance - %.4f" %
                             (coin_name, balance["available"], balance["trade_in_use"], balance["balance"]))
