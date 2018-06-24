import logging
from api.currency import Currency
from trader.market_manager.market_manager import MarketManager
from analyzer.analyzer import BasicAnalyzer


######################################################################
# get optimized spread
# by considering both "price[index]" and "qty_avail[index])"
######################################################################

def buy_sell_strategy_2(co_mm: MarketManager, co_currency: Currency, kb_mm: MarketManager, kb_currency: Currency):
    co_orderbook = co_mm.get_orderbook(co_currency)
    co_minask_price, co_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(co_orderbook)

    kb_orderbook = kb_mm.get_orderbook(kb_currency)
    kb_minask_price, kb_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(kb_orderbook)

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

    new_spread = BasicAnalyzer.calc_spread(co_buy_price, co_mm.market_fee,
                                           kb_sell_price, kb_mm.market_fee)
    rev_spread = BasicAnalyzer.calc_spread(kb_buy_price, kb_mm.market_fee,
                                           co_sell_price, co_mm.market_fee)

    return new_spread, rev_spread, co_buy_price, co_sell_price, kb_buy_price, kb_sell_price
