import time
import logging
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.market.market import Market
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.virtual_market_manager import VirtualMarketManager
from trader.trade_manager.order_watcher_stats import OrderWatcherStats
from trader.trade_manager.trade_manager import TradeManager
from config.global_conf import Global
from analyzer.analyzer import Analyzer

"""
!!! IMPORTANT NOTE !!!

[NEW Spread] => buy in mm1, sell in mm2
[REV Spread] => buy in mm2, sell in mm1

MODIFY config.global_conf > COIN_FILTER_FOR_BALANCE for balance creation!
"""


class RiskFreeArbBot:
    # maxbid에 사서 minask에 파는 시장가 전략 이용
    TARGET_STRATEGY = Analyzer.buy_sell_strategy_1

    TARGET_CURRENCY = "eth"
    COIN_TRADING_UNIT = 0.01
    TRADE_INTERVAL_IN_SEC = 3
    NEW_SPREAD_THRESHOLD = 0
    REV_SPREAD_THRESHOLD = 0
    # 향후에 거래량을 보고 결정할 parameter, 0.01로 거래한다는 가정하에 0.03으로 설정
    SLIPPAGE_HEDGE = 0.03

    def __init__(self, should_db_logging: bool = True,
                 is_backtesting: bool = False, start_time: int = None, end_time: int = None):
        self.is_backtesting = is_backtesting

        # init market managers
        if not self.is_backtesting:
            self.mm1 = CoinoneMarketManager()
            self.mm2 = KorbitMarketManager()
            OrderWatcherStats.initialize()
        else:
            self.mm1 = VirtualMarketManager(Market.VIRTUAL_CO, 0.001, 60000, 0.1)
            self.mm2 = VirtualMarketManager(Market.VIRTUAL_KB, 0.002, 60000, 0.1)

        self.trade_manager = TradeManager(should_db_logging=should_db_logging, is_backtesting=is_backtesting)
        self.loop_count = 0
        self.new_oppty_counter = 0
        self.rev_oppty_counter = 0

        self.new_trades = []
        self.rev_trades = []

        # set market currency
        self.mm1_currency = self.mm1.get_market_currency(self.TARGET_CURRENCY)
        self.mm2_currency = self.mm2.get_market_currency(self.TARGET_CURRENCY)

    def run(self):
        Global.configure_default_root_logging()

        # log initial balance
        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(self.mm1.get_balance())
        logging.info(self.mm2.get_balance())

        # jump into start loop
        while True:
            try:
                self.execute_trade_loop()
            except Exception as e:
                Global.send_to_slack_channel("Something happened to StatArbBot! Now it's dying from ... %s" % e)
                # stop order watcher stats thread
                OrderWatcherStats.instance().tear_down()
                raise e

    def execute_trade_loop(self, mm1_data=None, mm2_data=None):
        # print trade loop seq
        self.loop_count += 1
        logging.info("========== [# %12d Trade Loop] =================================================="
                     % self.loop_count)
        loop_start_time = time.time()
        trade = None

        # get current spread
        new_spread, rev_spread, \
        mm1_minask_price, mm1_maxbid_price, mm2_minask_price, mm2_maxbid_price, \
        mm1_minask_amount, mm1_maxbid_amount, mm2_minask_amount, mm2_maxbid_amount = \
            self.TARGET_STRATEGY(self.mm1, self.mm1_currency, self.mm2, self.mm2_currency)

        # log stat
        logging.info("[STAT][%s] min_ask: %d, max_bid: %d" % (self.mm1.get_market_name(),
                                                              mm1_minask_price, mm1_maxbid_price))
        logging.info("[STAT][%s] min_ask: %d, max_bid: %d" % (self.mm2.get_market_name(),
                                                              mm2_minask_price, mm2_maxbid_price))
        logging.info("[STAT] new_spread: %d, rev_spread: %d" % (new_spread, rev_spread))

        # calculate needed krw
        mm1_buy_krw = self.mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm1_minask_price
        mm2_buy_krw = self.mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm2_minask_price

        mm1_buy_price = mm1_minask_price
        mm1_sell_price = mm1_maxbid_price
        mm2_buy_price = mm2_minask_price
        mm2_sell_price = mm2_maxbid_price

        new_trade_count = len(self.new_trades)
        rev_trade_count = len(self.rev_trades)

        # sell coin if there is decline over one to another
        # if there's more new trades than rev trades => there's more coin than krw in mm1
        if new_trade_count > rev_trade_count:
            for new_trade in self.new_trades:
                if (
                        mm1_sell_price >= new_trade["sell_price"]
                        and self.mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                        and mm1_maxbid_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
                ):
                    self.mm1.order_sell(self.mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)
                    self.new_trades.remove(new_trade)
        # if there's more rev trades than new trades => there's more coin than krw in mm2
        elif rev_trade_count > new_trade_count:
            for rev_trade in self.rev_trades:
                if (
                        mm2_sell_price >= rev_trade["sell_price"]
                        and self.mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                        and mm2_maxbid_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
                ):
                    self.mm2.order_sell(self.mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
                    self.rev_trades.remove(rev_trade)

        # make decision
        if (
                new_spread > self.NEW_SPREAD_THRESHOLD
                and self.mm1.has_enough_coin("krw", mm1_buy_krw)
                and self.mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                and mm1_minask_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
                and mm2_maxbid_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
        ):
            logging.warning("[EXECUTE] New")
            buy_order = self.mm1.order_buy(self.mm1_currency, mm1_buy_price, self.COIN_TRADING_UNIT)
            sell_order = self.mm2.order_sell(self.mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
            trade = Trade(TradeTag.NEW, [buy_order, sell_order], TradeMeta({"sell_price": mm2_sell_price}))
            self.new_trades.append(trade)
        elif (
                rev_spread > self.REV_SPREAD_THRESHOLD
                and self.mm2.has_enough_coin("krw", mm2_buy_krw)
                and self.mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                and mm2_minask_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
                and mm1_maxbid_amount >= self.COIN_TRADING_UNIT + self.SLIPPAGE_HEDGE
        ):
            logging.warning("[EXECUTE] Reverse")
            buy_order = self.mm2.order_buy(self.mm2_currency, mm2_buy_price, self.COIN_TRADING_UNIT)
            sell_order = self.mm1.order_sell(self.mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)
            trade = Trade(TradeTag.REV, [buy_order, sell_order], TradeMeta({"sell_price": mm1_sell_price}))
            self.rev_trades.append(trade)
        else:
            logging.warning("[EXECUTE] No")

        # if there was any trade
        if trade is not None:
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

        # sleep for diff between the set interval and execution time
        loop_end_time = time.time()
        loop_spent_time = loop_end_time - loop_start_time
        sleep_time = self.TRADE_INTERVAL_IN_SEC - loop_spent_time
        if sleep_time > 0 and not self.is_backtesting:
            time.sleep(sleep_time)
