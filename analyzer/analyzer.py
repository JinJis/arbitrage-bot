import math
import logging
from api.currency import Currency
from trader.market.balance import Balance
from trader.market_manager.market_manager import MarketManager, Market
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator


class Analyzer:

    @staticmethod
    def calc_spread(buy_price: int, buy_fee: float, sell_price: int, sell_fee: float):
        return (-1) * buy_price / (1 - buy_fee) + (+1) * sell_price * (1 - sell_fee)

    @staticmethod
    def get_price_of_minask_maxbid(orderbook: dict):
        return int(orderbook["asks"][0]["price"].to_decimal()), \
               int(orderbook["bids"][0]["price"].to_decimal())

    @staticmethod
    def get_amount_of_minask_maxbid(orderbook: dict):
        return float(orderbook["asks"][0]["amount"].to_decimal()), \
               float(orderbook["bids"][0]["amount"].to_decimal())

    ######################################################################
    # buy at minask, sell at maxbid
    ######################################################################

    @staticmethod
    def buy_sell_strategy_1(mm1_orderbook: dict, mm2_orderbook: dict, mm1_market_fee: float, mm2_market_fee: float):
        mm1_minask_price, mm1_maxbid_price = Analyzer.get_price_of_minask_maxbid(mm1_orderbook)
        mm1_minask_amount, mm1_maxbid_amount = Analyzer.get_amount_of_minask_maxbid(mm1_orderbook)

        mm2_minask_price, mm2_maxbid_price = Analyzer.get_price_of_minask_maxbid(mm2_orderbook)
        mm2_minask_amount, mm2_maxbid_amount = Analyzer.get_amount_of_minask_maxbid(mm2_orderbook)

        # new => buy in mm1, sell in mm2
        new_spread = Analyzer.calc_spread(mm1_minask_price, mm1_market_fee,
                                          mm2_maxbid_price, mm2_market_fee)
        # rev => buy in mm2, sell in mm1
        rev_spread = Analyzer.calc_spread(mm2_minask_price, mm2_market_fee,
                                          mm1_maxbid_price, mm1_market_fee)

        return new_spread, rev_spread, \
               mm1_minask_price, mm1_maxbid_price, \
               mm2_minask_price, mm2_maxbid_price, \
               mm1_minask_amount, mm1_maxbid_amount, \
               mm2_minask_amount, mm2_maxbid_amount

    ######################################################################
    # co:   buy at ma_mb_avg ±      sell at ma_mb_avg ±
    # kb:   buy at (minask-50)     sell at (maxbid+50)
    ######################################################################

    @staticmethod
    def buy_sell_strategy_2(co_mm: MarketManager, co_currency: Currency, kb_mm: MarketManager, kb_currency: Currency):
        co_orderbook = co_mm.get_orderbook(co_currency)
        co_minask_price, co_maxbid_price = Analyzer.get_price_of_minask_maxbid(co_orderbook)

        kb_orderbook = kb_mm.get_orderbook(kb_currency)
        kb_minask_price, kb_maxbid_price = Analyzer.get_price_of_minask_maxbid(kb_orderbook)

        logging.info(
            "[STAT][%s] min_ask: %d, max_bid: %d" % (co_mm.get_market_name(), co_minask_price, co_maxbid_price))
        logging.info(
            "[STAT][%s] min_ask: %d, max_bid: %d" % (kb_mm.get_market_name(), kb_minask_price, kb_maxbid_price))

        # set co buy & sell price
        co_ma_mb_diff = co_minask_price - co_maxbid_price
        step_count_from_mid = 5  # fill difficulty: -5 hard ~ 5 easy
        co_buy_price = co_maxbid_price + int(co_ma_mb_diff * (5 + step_count_from_mid) / 10)
        co_sell_price = co_maxbid_price + int(co_ma_mb_diff * (5 - step_count_from_mid) / 10)

        # set kb buy & sell price
        kb_buy_price = kb_minask_price - 50
        kb_sell_price = kb_maxbid_price + 50

        new_spread = Analyzer.calc_spread(co_buy_price, co_mm.market_fee,
                                          kb_sell_price, kb_mm.market_fee)
        rev_spread = Analyzer.calc_spread(kb_buy_price, kb_mm.market_fee,
                                          co_sell_price, co_mm.market_fee)

        return new_spread, rev_spread, co_buy_price, co_sell_price, kb_buy_price, kb_sell_price

    @staticmethod
    def get_ticker_log_spread(mm1_ticker: dict, mm2_ticker: dict):
        mm1_last = int(mm1_ticker["last"].to_decimal())
        mm2_last = int(mm2_ticker["last"].to_decimal())
        log_spread = math.log(mm1_last) - math.log(mm2_last)
        return log_spread, mm1_last, mm2_last

    @staticmethod
    def get_orderbook_mid_price_log_spread(mm1_orderbook: dict, mm2_orderbook: dict):
        mm1_mid_price, _, _ = Analyzer.get_orderbook_mid_price(mm1_orderbook)
        mm2_mid_price, _, _ = Analyzer.get_orderbook_mid_price(mm2_orderbook)

        # round to 2 decimals
        mm1_mid_price = round(mm1_mid_price / 100) * 100
        mm2_mid_price = round(mm2_mid_price / 100) * 100

        log_spread = math.log(mm1_mid_price) - math.log(mm2_mid_price)
        return log_spread, mm1_mid_price, mm2_mid_price

    @staticmethod
    def get_orderbook_mid_price(orderbook: dict):
        minask = int(orderbook["asks"][0]["price"].to_decimal())
        maxbid = int(orderbook["bids"][0]["price"].to_decimal())
        mid_price = (minask + maxbid) / 2
        return mid_price, minask, maxbid

    @staticmethod
    def get_orderbook_mid_vwap(orderbook: dict, depth: int):
        vwap = dict()
        for key in ("asks", "bids"):
            items = orderbook[key]
            volume_sum = 0
            weighted_sum = 0
            for i in range(depth):
                price = int(items[i]["price"].to_decimal())
                volume = float(items[i]["amount"].to_decimal())
                volume_sum += volume
                weighted_sum += price * volume
            vwap[key] = weighted_sum / volume_sum
        ask_vwap = vwap["asks"]
        bid_vwap = vwap["bids"]
        mid_vwap = (ask_vwap + bid_vwap) / 2
        return mid_vwap, ask_vwap, bid_vwap

    @staticmethod
    def combine_balance(mm1_balance: Balance, mm2_balance: Balance, target_coins: tuple):
        mm1_balance_dict = mm1_balance.to_dict()
        mm2_balance_dict = mm2_balance.to_dict()

        result = dict()
        for coin in target_coins:
            mm1_coin_balance = mm1_balance_dict[coin]
            mm2_coin_balance = mm2_balance_dict[coin]
            result[coin.upper()] = {
                "available": mm1_coin_balance["available"] + mm2_coin_balance["available"],
                "trade_in_use": mm1_coin_balance["trade_in_use"] + mm2_coin_balance["trade_in_use"],
                "balance": mm1_coin_balance["balance"] + mm2_coin_balance["balance"]
            }
        return result

    @staticmethod
    def have_enough_balance_for_arb(buy_mm: MarketManager, sell_mm: MarketManager,
                                    buy_price: int, coin_trade_amount: float, coin_currency: str):
        buy_mm_needed_krw = coin_trade_amount * buy_price
        sell_mm_needed_coin = coin_trade_amount
        return (buy_mm.has_enough_coin("krw", buy_mm_needed_krw) and
                sell_mm.has_enough_coin(coin_currency, sell_mm_needed_coin))

    @staticmethod
    def get_fee_consideration(buy_market: Market, currency: str) -> (float, bool):
        fee = GlobalFeeAccumulator.get_fee(buy_market, currency)
        # round down to #4 decimal
        rounded_fee = math.floor(fee * 10000) / 10000
        # 0.0001 is the smallest order unit in coinone
        if rounded_fee >= 0.0001:
            return rounded_fee, True
        return 0, False
