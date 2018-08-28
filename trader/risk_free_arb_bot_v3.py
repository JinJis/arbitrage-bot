import logging
import pymongo
from pymongo.collection import Collection
from analyzer.trade_analyzer import ATSAnalyzer
from analyzer.trade_analyzer import SpreadInfo
from config.global_conf import Global
from trader.base_arb_bot import BaseArbBot
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.market_manager.market_manager import MarketManager
from trader.trade_manager.order_watcher_stats import OrderWatcherStats


class RiskFreeArbBotV3(BaseArbBot):

    def __init__(
            self, mm1: MarketManager, mm2: MarketManager, target_currency: str,
            initial_settings_col: Collection, trade_interval_col: Collection):

        self.initial_settings_col = initial_settings_col
        self.trade_interval_col = trade_interval_col
        self.trade_strategy = ATSAnalyzer.actual_tradable_spread_strategy
        super().__init__(mm1, mm2, target_currency)

    def run(self):
        logging.info("========== [  INITIAL BALANCE  ] ========================================================")
        logging.info(self.mm1.get_balance())
        logging.info(self.mm2.get_balance())

        while True:
            try:
                self.execute_trade_loop()
            except Exception as e:
                Global.send_to_slack_channel("Something happened to RFAB! Now it's dying from ... %s" % e)
                # stop order watcher stats thread
                OrderWatcherStats.instance().tear_down()
                raise e

    def actual_trade_loop(self, mm1_data=None, mm2_data=None):
        # read latest initial settings from db
        ini_set = self.initial_settings_col.find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )
        # read latest trade interval from db
        trade_interval = self.trade_interval_col.find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )["trade_interval"]
        # reset trade interval
        self.trade_interval_in_sec = trade_interval

        # get orderbook data
        mm1_data = self.mm1.get_orderbook(self.target_currency)
        mm2_data = self.mm2.get_orderbook(self.target_currency)

        # get spread info from given trade strategy
        result = self.trade_strategy(
            mm1_data,
            mm2_data,
            self.mm1.taker_fee,
            self.mm2.taker_fee,
            ini_set["max_trading_coin"]
        )
        new_spread_info: SpreadInfo = result["new"]
        rev_spread_info: SpreadInfo = result["rev"]

        # init checker
        new_trade = None
        rev_trade = None

        # NEW
        if new_spread_info.spread_in_unit > 0:
            if new_spread_info.able_to_trade:
                new_trade = self.execute_trade(ini_set, new_spread_info, "new")
                self.add_trade(new_trade)

        # REVERSE
        if rev_spread_info.spread_in_unit > 0:
            if rev_spread_info.able_to_trade:
                rev_trade = self.execute_trade(ini_set, rev_spread_info, "rev")
                self.add_trade(rev_trade)

        # update balance if there was any trade
        if new_trade or rev_trade:
            self.mm1.update_balance()
            self.mm2.update_balance()

    def execute_trade(self, ini_set: dict, spread_info: SpreadInfo, trade_type: str = "new" or "rev"):
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

        if not buying_mkt.is_bigger_than_min_trading_coin(spread_info.buy_order_amt, self.target_currency):
            logging.info("buy amount smaller than min trading coin: %d" % spread_info.buy_order_amt)
            return None

        if not selling_mkt.is_bigger_than_min_trading_coin(spread_info.sell_order_amt, self.target_currency):
            logging.info("sell amount smaller than min trading coin: %d" % spread_info.sell_order_amt)
            return None

        # check condition
        threshold_cond = spread_info.spread_to_trade >= ini_set[trade_type]["threshold"]

        buy_min_cond = (spread_info.buy_order_amt >= buying_mkt.min_trading_coin)
        sell_min_cond = (spread_info.sell_order_amt >= selling_mkt.min_trading_coin)
        min_coin_cond = (buy_min_cond and sell_min_cond)

        # quit if conditions don't meet
        if not threshold_cond:
            logging.info("spread threshold condition not met!")
            return None
        if not min_coin_cond:
            logging.info("min coin condition not met!")
            return None

        # balance check
        krw_needed = spread_info.buy_unit_price * spread_info.buy_order_amt
        coin_needed = spread_info.sell_order_amt
        has_enough_krw = self.has_enough_coin_checker(buying_mkt, "krw", krw_needed)
        has_enough_coin = self.has_enough_coin_checker(selling_mkt, self.target_currency, coin_needed)

        # not enough krw
        if not has_enough_krw:
            logging.info("Not enough KRW in buying market!")
            return None

        # not enough coin
        if not has_enough_coin:
            logging.info("Not enough COIN in selling market!")
            return None

        # make buy & sell order
        buy_order = buying_mkt.order_buy(buying_currency, spread_info.buy_unit_price, spread_info.buy_order_amt)
        sell_order = selling_mkt.order_sell(selling_currency, spread_info.sell_unit_price, spread_info.sell_order_amt)
        return Trade(getattr(TradeTag, trade_type.upper()), [buy_order, sell_order], TradeMeta({}))
