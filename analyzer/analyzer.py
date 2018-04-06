from api.currency import Currency
from trader.market_manager.market_manager import MarketManager
import logging
import math
from trader.market.balance import Balance


class Analyzer:

    @staticmethod
    def calc_spread(buy_price: int, buy_fee: float, sell_price: int, sell_fee: float):
        return (-1) * buy_price / (1 - buy_fee) + (+1) * sell_price * (1 - sell_fee)

    @staticmethod
    def get_price_of_minask_maxbid(orderbook: dict):
        return int(orderbook["asks"][0]["price"].to_decimal()), int(orderbook["bids"][0]["price"].to_decimal())

    @staticmethod
    def get_amount_of_minask_maxbid(orderbook: dict, ask_index: int, bid_index: int):
        return float(orderbook["asks"][ask_index]["amount"].to_decimal()), float(
            orderbook["bids"][bid_index]["amount"].to_decimal())

    ######################################################################
    # buy at minask, sell at maxbid
    ######################################################################

    @staticmethod
    def buy_sell_strategy_1(mm1: MarketManager, mm1_currency: Currency, mm2: MarketManager, mm2_currency: Currency):
        mm1_orderbook = mm1.get_orderbook(mm1_currency)
        mm1_minask_price, mm1_maxbid_price = Analyzer.get_price_of_minask_maxbid(mm1_orderbook)
        mm1_minask_amount, mm1_maxbid_amount = Analyzer.get_amount_of_minask_maxbid(mm1_orderbook, 0, 0)

        mm2_orderbook = mm2.get_orderbook(mm2_currency)
        mm2_minask_price, mm2_maxbid_price = Analyzer.get_price_of_minask_maxbid(mm2_orderbook)
        mm2_minask_amount, mm2_maxbid_amount = Analyzer.get_amount_of_minask_maxbid(mm1_orderbook, 0, 0)

        new_spread = Analyzer.calc_spread(mm1_minask_price, mm1.market_fee,
                                          mm2_maxbid_price, mm2.market_fee)
        rev_spread = Analyzer.calc_spread(mm2_minask_price, mm2.market_fee,
                                          mm1_maxbid_price, mm1.market_fee)

        mm1_buy_price = mm1_minask_price
        mm1_sell_price = mm1_maxbid_price
        mm2_buy_price = mm2_minask_price
        mm2_sell_price = mm2_maxbid_price

        return new_spread, rev_spread, mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price, \
               mm1_minask_amount, mm1_maxbid_amount, mm2_minask_amount, mm2_maxbid_amount

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
        mm1_minask = int(mm1_orderbook["asks"][0]["price"].to_decimal())
        mm1_maxbid = int(mm1_orderbook["bids"][0]["price"].to_decimal())
        mm1_mid_price = (mm1_minask + mm1_maxbid) / 2

        mm2_minask = int(mm2_orderbook["asks"][0]["price"].to_decimal())
        mm2_maxbid = int(mm2_orderbook["bids"][0]["price"].to_decimal())
        mm2_mid_price = (mm2_minask + mm2_maxbid) / 2

        log_spread = math.log(mm1_mid_price) - math.log(mm2_mid_price)
        return log_spread, mm1_mid_price, mm2_mid_price

    @staticmethod
    def combine_balance(mm1_balance: Balance, mm2_balance: Balance, target_coins: tuple = ("eth", "krw")):
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
        buy_mm_needed_krw = buy_mm.calc_actual_coin_need_to_buy(coin_trade_amount) * buy_price
        sell_mm_needed_coin = coin_trade_amount
        return (buy_mm.has_enough_coin("krw", buy_mm_needed_krw) and
                sell_mm.has_enough_coin(coin_currency, sell_mm_needed_coin))
