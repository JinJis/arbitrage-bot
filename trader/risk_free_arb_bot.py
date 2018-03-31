import time
import logging
from trader.market_manager.market_manager import MarketManager
from trader.market_manager.coinone_market_manager import CoinoneMarketManager
from trader.market_manager.korbit_market_manager import KorbitMarketManager
from trader.market_manager.virtual_market_manager import VirtualMarketManager, VirtualMarketApiType
from config.global_conf import Global
from analyzer.analyzer import Analyzer

"""
!!! IMPORTANT NOTE !!!

[NEW Spread] => buy in mm1, sell in mm2
[REV Spread] => buy in mm2, sell in mm1

MODIFY config.global_conf > COIN_FILTER_FOR_BALANCE for balance creation!
"""

class RiskFreeArbBot:
    TARGET_CURRENCY = "eth"
    COIN_TRADING_UNIT = 0.01
    TRADE_INTERVAL_IN_SEC = 3
    
    # maxbid에 사서 minask에 파는 시장가 전략 이용
    TARGET_STRATEGY = Analyzer.buy_sell_strategy_1
    NEW_SPREAD_THRESHOLD = 0
    REV_SPREAD_THRESHOLD = 0

    def __init__(self):
        # init market managers
        # self.coinone_mm = CoinoneMarketManager()
        # self.korbit_mm = KorbitMarketManager()
        self.v_coinone_mm = VirtualMarketManager("co", VirtualMarketApiType.COINONE, 0.001, 60000, 0.1)
        self.v_korbit_mm = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT, 0.002, 60000, 0.1)
        # self.v_korbit_mm = VirtualMarketManager("kb", VirtualMarketApiType.KORBIT, 0.0008, 60000, 0.1)

        self.new_spread_orders = []
        self.new_spread_count = 0
        self.reverse_spread_orders = []
        self.reverse_spread_count = 0
        self.slippage_hedge = 0.03

    def run(self):
        Global.configure_default_root_logging()
        self.execute(self.v_coinone_mm, self.v_korbit_mm, RiskFreeArbBot.TARGET_STRATEGY)

    def execute(self, mm1: MarketManager, mm2: MarketManager, strategy_fun):
        # get currency for each market
        mm1_currency = mm1.get_market_currency(self.TARGET_CURRENCY)
        mm2_currency = mm2.get_market_currency(self.TARGET_CURRENCY)

        # log initial balance
        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(mm1.get_balance())
        logging.info(mm2.get_balance())

        # init loop count
        loop_count = 1

        while True:
            # print trade loop seq
            logging.info("========== [# %12d Trade Loop] =================================================="
                         % loop_count)
            loop_count += 1

            # get current spread
            new_spread, rev_spread, mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price, \
            mm1_minask_amount, mm1_maxbid_amount, mm2_minask_amount, mm2_maxbid_amount = strategy_fun(mm1, mm1_currency, mm2, mm2_currency)

            # log stat
            logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (mm1.get_market_name(),
                                                                       mm1_buy_price, mm1_sell_price))
            logging.info("[STAT][%s] buy_price: %d, sell_price: %d" % (mm2.get_market_name(),
                                                                       mm2_buy_price, mm2_sell_price))
            logging.info("[STAT] new_spread: %d, rev_spread: %d" % (new_spread, rev_spread))

            # calculate needed krw
            mm1_buy_krw = mm1.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm1_buy_price
            mm2_buy_krw = mm2.calc_actual_coin_need_to_buy(self.COIN_TRADING_UNIT) * mm2_buy_price

            # sell coin in more markets
            # self.slippage_hedge 는 향후에 거래량을 보고 결정할 parameter, 0.01로 거래한다는 가정하에 0.03으로 설정 
            if (self.new_spread_count >= self.reverse_spread_count):
                for new_spread_order in self.new_spread_orders:
                    if (
                            mm1_sell_price >= new_spread_order["sell_price"]
                            and mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                            and mm1_maxbid_amount >= self.COIN_TRADING_UNIT + self.slippage_hedge
                    ):
                        mm1.order_sell(mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT)
                        self.new_spread_orders.remove(new_spread_order)
            else:
                for reverse_spread_order in self.reverse_spread_orders:
                    if (
                            mm2_sell_price >= reverse_spread_order["sell_price"]
                            and mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                            and mm2_maxbid_amount >= self.COIN_TRADING_UNIT + self.slippage_hedge
                    ):  
                        mm2.order_sell(mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT)
                        self.reverse_spread_orders.remove(reverse_spread_order)

            # make decision
            if (
                    new_spread > self.NEW_SPREAD_THRESHOLD
                    and mm1.has_enough_coin("krw", mm1_buy_krw)
                    and mm2.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                    and mm1_minask_amount >= self.COIN_TRADING_UNIT + self.slippage_hedge
                    and mm2_maxbid_amount >= self.COIN_TRADING_UNIT + self.slippage_hedge
            ):
                logging.warning("[EXECUTE] New")
                new_spread_order = {
                    "order_buy": mm1.order_buy(mm1_currency, mm1_buy_price, self.COIN_TRADING_UNIT),
                    "order_sell": mm2.order_sell(mm2_currency, mm2_sell_price, self.COIN_TRADING_UNIT),
                    "sell_price": mm2_sell_price 
                }
                self.new_spread_orders.append(new_spread_order)
                self.new_spread_count += 1
            elif (
                    rev_spread > self.REV_SPREAD_THRESHOLD
                    and mm2.has_enough_coin("krw", mm2_buy_krw)
                    and mm1.has_enough_coin(self.TARGET_CURRENCY, self.COIN_TRADING_UNIT)
                    and mm2_minask_amount >= self.COIN_TRADING_UNIT + self.slippage_hedge
                    and mm1_maxbid_amount >= self.COIN_TRADING_UNIT + self.slippage_hedge
            ):
                logging.warning("[EXECUTE] Reverse")

                reverse_spread_order = {
                    "order_buy": mm2.order_buy(mm2_currency, mm2_buy_price, self.COIN_TRADING_UNIT),
                    "order_sell": mm1.order_sell(mm1_currency, mm1_sell_price, self.COIN_TRADING_UNIT),
                    "sell_price": mm1_sell_price 
                }
                self.reverse_spread_orders.append(reverse_spread_order)
                self.reverse_spread_count += 1
            else:
                logging.warning("[EXECUTE] No")

            # log combined balance
            Analyzer.log_combined_balance(mm1.get_balance(), mm2.get_balance())

            # sleep for interval
            time.sleep(self.TRADE_INTERVAL_IN_SEC)

RiskFreeArbBot().run()