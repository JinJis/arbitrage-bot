from api.currency import Currency
from trader.market_manager.market_manager import MarketManager


class Analyzer:

    @staticmethod
    def calc_spread(buy_price: int, buy_fee: float, sell_price: int, sell_fee: float):
        return (-1) * buy_price / (1 - buy_fee) + (+1) * sell_price * (1 - sell_fee)

    @staticmethod
    def get_price_of_minask_maxbid(orderbook: dict):
        return int(orderbook["asks"][0]["price"].to_decimal()), int(orderbook["bids"][0]["price"].to_decimal())

    ########################################
    # buy at minask, sell at maxbid
    ########################################

    @staticmethod
    def buy_sell_strategy_1(mm1: MarketManager, mm1_currency: Currency, mm2: MarketManager, mm2_currency: Currency):
        mm1_orderbook = mm1.get_orderbook(mm1_currency)
        mm1_minask_price, mm1_maxbid_price = Analyzer.get_price_of_minask_maxbid(mm1_orderbook)

        mm2_orderbook = mm2.get_orderbook(mm2_currency)
        mm2_minask_price, mm2_maxbid_price = Analyzer.get_price_of_minask_maxbid(mm2_orderbook)

        new_spread = Analyzer.calc_spread(mm1_minask_price, mm1.market_fee,
                                          mm2_maxbid_price, mm2.market_fee)
        rev_spread = Analyzer.calc_spread(mm2_minask_price, mm2.market_fee,
                                          mm1_maxbid_price, mm1.market_fee)

        mm1_buy_price = mm1_minask_price
        mm1_sell_price = mm1_maxbid_price
        mm2_buy_price = mm2_minask_price
        mm2_sell_price = mm2_maxbid_price

        return new_spread, rev_spread, mm1_buy_price, mm1_sell_price, mm2_buy_price, mm2_sell_price
