import logging
import pymongo
from pymongo.collection import Collection
from analyzer.trade_analyzer import MCTSAnalyzer
from analyzer.trade_analyzer import SpreadInfo
from config.global_conf import Global
from trader.base_arb_bot import BaseArbBot
from trader.market.trade import Trade, TradeTag, TradeMeta
from trader.market_manager.market_manager import MarketManager


class RiskFreeArbBotV4(BaseArbBot):

    def __init__(
            self, mm1: MarketManager, mm2: MarketManager, target_currency: str, streamer_db: Collection):

        self.trade_commander_col = streamer_db["trade_commander"]
        self.trade_strategy = MCTSAnalyzer.min_coin_tradable_spread_strategy

        super().__init__(mm1, mm2, target_currency)

    def run(self):
        while True:
            self.execute_trade_loop()

    def actual_trade_loop(self, mm1_data=None, mm2_data=None):

        # get latest trade_commander dict from db
        trade_commander_set = self.trade_commander_col.find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )

        # check if settlement reached
        if trade_commander_set["settlement"] is True:
            raise EnvironmentError

        # check if time flow rate under exhaustion rate
        if trade_commander_set["execute_trade"] is False:
            logging.warning("Trade Streamer decided not to trade.. check below to see what caused this decision")
            logging.warning("[TimeFlow > Exhaust]: %s"
                            % trade_commander_set["is_time_flow_above_exhaust"])
            logging.warning("[Under Opportunity]: %s"
                            % trade_commander_set["is_oppty"])
            return

        if trade_commander_set["execute_trade"] is True:
            pass

        # get orderbook data
        mm1_data = self.mm1.get_orderbook(self.mm1_currency)
        mm2_data = self.mm2.get_orderbook(self.mm2_currency)

        # get spread info from given trade strategy
        result = self.trade_strategy(
            mm1_data,
            mm2_data,
            self.mm1.taker_fee,
            self.mm2.taker_fee,
            trade_commander_set["streamer_mctu"]
        )
        new_spread_info: SpreadInfo = result["new"]
        rev_spread_info: SpreadInfo = result["rev"]

        # init checker
        new_trade = None
        rev_trade = None

        # NEW
        if new_spread_info.spread_in_unit > 0:
            if new_spread_info.able_to_trade:
                new_trade = self.execute_trade(new_spread_info, trade_commander_set["mctu_spread_threshold"], "new")
                self.add_trade(new_trade)

        # REVERSE
        if rev_spread_info.spread_in_unit > 0:
            if rev_spread_info.able_to_trade:
                rev_trade = self.execute_trade(rev_spread_info, trade_commander_set["mctu_spread_threshold"], "rev")
                self.add_trade(rev_trade)

        # update balance if there was any trade
        if new_trade or rev_trade:
            self.mm1.update_balance()
            self.mm2.update_balance()

    def execute_trade(self, spread_info: SpreadInfo, mctu_spread_threshold: float, trade_type: str = "new" or "rev"):
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
            logging.warning("buy amount smaller than min trading coin: %d" % spread_info.buy_order_amt)
            return None

        if not selling_mkt.is_bigger_than_min_trading_coin(spread_info.sell_order_amt, self.target_currency):
            logging.warning("sell amount smaller than min trading coin: %d" % spread_info.sell_order_amt)
            return None

        # obey each order amount to exchange min order digit
        spread_info.buy_order_amt = round(spread_info.buy_order_amt,
                                          Global.read_min_order_digit(buying_mkt.get_market_name()))
        spread_info.sell_order_amt = round(spread_info.sell_order_amt,
                                           Global.read_min_order_digit(selling_mkt.get_market_name()))

        # check condition
        threshold_cond = spread_info.spread_to_trade >= mctu_spread_threshold

        # quit if conditions don't meet
        if not threshold_cond:
            logging.warning("spread threshold condition not met!")
            return None

        # balance check
        krw_needed = spread_info.buy_unit_price * spread_info.buy_order_amt
        coin_needed = spread_info.sell_order_amt
        has_enough_krw = self.has_enough_coin_checker(buying_mkt, "krw", krw_needed)
        has_enough_coin = self.has_enough_coin_checker(selling_mkt, self.target_currency, coin_needed)

        # not enough krw
        if not has_enough_krw:
            logging.warning("Not enough KRW in buying market!")
            return None

        # not enough coin
        if not has_enough_coin:
            logging.warning("Not enough COIN in selling market!")
            return None

        # make buy & sell order
        logging.critical("========[ Successful Trade INFO ]========================")
        logging.critical("Spread Traded: %.2f" % spread_info.spread_to_trade)
        logging.critical("Buying Price: %.2f" % spread_info.buy_unit_price)
        logging.critical("Buying Amount: %f" % spread_info.buy_order_amt)
        logging.critical("Selling Price: %.2f" % spread_info.sell_unit_price)
        logging.critical("Selling Price: %f" % spread_info.sell_order_amt)

        buy_order = buying_mkt.order_buy(buying_currency, spread_info.buy_unit_price, spread_info.buy_order_amt)
        sell_order = selling_mkt.order_sell(selling_currency, spread_info.sell_unit_price, spread_info.sell_order_amt)
        return Trade(getattr(TradeTag, trade_type.upper()), [buy_order, sell_order], TradeMeta({}))
