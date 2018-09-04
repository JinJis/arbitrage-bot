import math
from trader.market.balance import Balance
from trader.market_manager.market_manager import MarketManager, Market
from trader.market_manager.global_fee_accumulator import GlobalFeeAccumulator

"""Basic Analyzer for trading, balancing and execution for RFAB1,2"""


class BasicAnalyzer:
    @staticmethod
    def calc_spread(buy_price: int, buy_fee: float, sell_price: int, sell_fee: float):
        return (-1) * buy_price / (1 - buy_fee) + (+1) * sell_price * (1 - sell_fee)

    @staticmethod
    def get_price_of_minask_maxbid(orderbook: dict):
        return int(orderbook["asks"][0]["price"].to_decimal()), int(orderbook["bids"][0]["price"].to_decimal())

    @staticmethod
    def get_amount_of_minask_maxbid(orderbook: dict):
        return float(orderbook["asks"][0]["amount"].to_decimal()), float(orderbook["bids"][0]["amount"].to_decimal())

        ######################################################################
        # buy at minask, sell at maxbid
        ######################################################################

    @staticmethod
    def buy_sell_strategy_1(mm1_orderbook: dict, mm2_orderbook: dict, mm1_market_fee: float, mm2_market_fee: float):
        mm1_minask_price, mm1_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(mm1_orderbook)
        mm1_minask_amount, mm1_maxbid_amount = BasicAnalyzer.get_amount_of_minask_maxbid(mm1_orderbook)

        mm2_minask_price, mm2_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(mm2_orderbook)
        mm2_minask_amount, mm2_maxbid_amount = BasicAnalyzer.get_amount_of_minask_maxbid(mm2_orderbook)

        # new => buy in mm1, sell in mm2
        new_spread = BasicAnalyzer.calc_spread(mm1_minask_price, mm1_market_fee,
                                               mm2_maxbid_price, mm2_market_fee)
        # rev => buy in mm2, sell in mm1
        rev_spread = BasicAnalyzer.calc_spread(mm2_minask_price, mm2_market_fee,
                                               mm1_maxbid_price, mm1_market_fee)

        return (new_spread, rev_spread, mm1_minask_price, mm1_maxbid_price, mm2_minask_price, mm2_maxbid_price,
                mm1_minask_amount, mm1_maxbid_amount, mm2_minask_amount, mm2_maxbid_amount)

    ######################################################################
    # co:   buy at ma_mb_avg ±      sell at ma_mb_avg ±
    # kb:   buy at (minask-50)     sell at (maxbid+50)
    ######################################################################

    @staticmethod
    def get_ticker_log_spread(mm1_ticker: dict, mm2_ticker: dict):
        mm1_last = int(mm1_ticker["last"].to_decimal())
        mm2_last = int(mm2_ticker["last"].to_decimal())
        log_spread = math.log(mm1_last) - math.log(mm2_last)
        return log_spread, mm1_last, mm2_last

    @staticmethod
    def get_orderbook_mid_price_log_spread(mm1_orderbook: dict, mm2_orderbook: dict):
        mm1_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(mm1_orderbook)
        mm2_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(mm2_orderbook)

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
                                    buy_price: (int or float), coin_trade_amount: float, coin_currency: str):
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


# Simplified version of OTS strategy.
# This considers amount of coin that each markets provide but do not optimize with oderbook indexes
class SpreadInfo:
    # spread_in_unit, spread_to_trade, buy_unit_price, sell_unit_price, buy_amt, sell_amt
    def __init__(self, able_to_trade: bool, spread_in_unit: float, spread_to_trade: float = None,
                 buy_unit_price: float = None, sell_unit_price: float = None,
                 buy_order_amt: float = None, sell_order_amt: float = None):
        self.able_to_trade = able_to_trade
        self.spread_in_unit = spread_in_unit
        self.spread_to_trade = spread_to_trade
        self.buy_unit_price = buy_unit_price
        self.sell_unit_price = sell_unit_price
        self.buy_order_amt = buy_order_amt
        self.sell_order_amt = sell_order_amt


class ATSAnalyzer:
    # Final ready-to-be-applied static function of "OTS strategy"
    # discarded getting optmized spread by calculating orderbook index depths
    @staticmethod
    def actual_tradable_spread_strategy(mm1_orderbook: dict, mm2_orderbook: dict,
                                        mm1_market_fee: float, mm2_market_fee: float,
                                        max_coin_trading_unit: float, min_trading_coin: int):
        mm1_minask_price, mm1_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(mm1_orderbook)
        mm1_minask_amount, mm1_maxbid_amount = BasicAnalyzer.get_amount_of_minask_maxbid(mm1_orderbook)

        mm2_minask_price, mm2_maxbid_price = BasicAnalyzer.get_price_of_minask_maxbid(mm2_orderbook)
        mm2_minask_amount, mm2_maxbid_amount = BasicAnalyzer.get_amount_of_minask_maxbid(mm2_orderbook)

        # new => buy in mm1, sell in mm2
        new_spread_info = ATSAnalyzer.get_actual_spread_info(mm1_minask_price, mm1_minask_amount, mm1_market_fee,
                                                             mm2_maxbid_price, mm2_maxbid_amount, mm2_market_fee,
                                                             max_coin_trading_unit, min_trading_coin)
        # rev => buy in mm2, sell in mm1
        rev_spread_info = ATSAnalyzer.get_actual_spread_info(mm2_minask_price, mm2_minask_amount, mm2_market_fee,
                                                             mm1_maxbid_price, mm1_maxbid_amount, mm1_market_fee,
                                                             max_coin_trading_unit, min_trading_coin)

        return {
            "new": new_spread_info,
            "rev": rev_spread_info
        }

    @staticmethod  # avail_amount = total amount of coin that specific mkt provides
    def get_actual_spread_info(buy_unit_price: (int or float), buy_avail_amount: float, buy_fee: float,
                               sell_unit_price: (int or float), sell_avail_amount: float, sell_fee: float,
                               max_trading_unit: float, min_trading_coin: int):
        # buy, sell 그리고 설정한 최대 거래 코인수 중 최소값이 거래되는 qty (tradable qty는 mm1, mm2에서 제공하는 qty에 모두 만족되는 양)
        tradable_qty = min(buy_avail_amount, sell_avail_amount, max_trading_unit)
        spread_in_unit = (-1) * buy_unit_price / (1 - buy_fee) + (+1) * sell_unit_price * (1 - sell_fee)

        if (tradable_qty < 0) or (buy_avail_amount == sell_avail_amount == max_trading_unit):
            return SpreadInfo(able_to_trade=False, spread_in_unit=spread_in_unit)

        # 여기 굉장히 중요!!! trade후 mm1, mm2 코인 수 합 정확히 유지해줘야함
        # buy하면 buy하는 코인 주문 amt에서 fee 차감되어 들어옴
        # sell은 코인 주문 amt 만큼 들어옴

        # 1)
        if tradable_qty == max_trading_unit:
            # if actual coin amt that will be transfered to buying account is less that max_trading_unit,
            # Don't trade
            if buy_avail_amount < tradable_qty / (1 - buy_fee):
                return SpreadInfo(able_to_trade=False, spread_in_unit=spread_in_unit)
            else:
                buy_amt = tradable_qty / (1 - buy_fee)
                sell_amt = tradable_qty

        # 2)
        elif tradable_qty == sell_avail_amount:
            # in case of sell and buy amt are same and tradable qty at the same time
            if buy_avail_amount < tradable_qty / (1 - buy_fee):
                if buy_avail_amount == sell_avail_amount:
                    buy_amt = tradable_qty
                    sell_amt = tradable_qty * (1 - buy_fee)
                else:
                    return SpreadInfo(able_to_trade=False, spread_in_unit=spread_in_unit)
            # if sell_amt is the sole tradable qty, which means the minimum amt
            else:
                buy_amt = tradable_qty / (1 - buy_fee)
                sell_amt = tradable_qty

        # 3)
        elif tradable_qty == buy_avail_amount:
            # if buy_avail_amt is the tradable_qty, no need to further analyze!
            buy_amt = tradable_qty
            sell_amt = tradable_qty * (1 - buy_fee)  # buy_fee로 계산해야 buy 쪽 코인이랑 수량 맞춰짐!!

        else:
            return SpreadInfo(able_to_trade=False, spread_in_unit=spread_in_unit)

        # finally, check with tradable min_trading_amt (max of mm1, mm2 min_trading_coin) with buy, sell amt
        if (buy_amt <= min_trading_coin) and (sell_amt <= min_trading_coin):
            return SpreadInfo(able_to_trade=False, spread_in_unit=spread_in_unit)

        # in unit은 코인 한개 거래시 스프레드. possible trading qty 곱해주면 (buy쪽 수수료 코인으로 차감되는 경우 감안) 실제 스프레드
        spread_to_trade = \
            (-1) * buy_unit_price * buy_amt * (1 - buy_fee) + (+1) * sell_unit_price * sell_amt * (1 - sell_fee)

        return SpreadInfo(able_to_trade=True,
                          spread_in_unit=spread_in_unit, spread_to_trade=spread_to_trade,
                          buy_unit_price=buy_unit_price, sell_unit_price=sell_unit_price,
                          buy_order_amt=buy_amt, sell_order_amt=sell_amt)


"""Initial Setting optimizer Analyzer"""


class ISOAnalyzer:

    @staticmethod
    def get_opt_initial_setting(result: list):
        # in case where
        if len(result) == 0:
            return None
        max_krw_pair = None
        # Get list of those results that have same KRW balance
        same_krw_list = []
        for pair in result:
            # 초기값 설정
            if max_krw_pair is None:
                max_krw_pair = pair
                same_krw_list.append(max_krw_pair)
                continue
            # 비교
            if pair["krw_earned"] > max_krw_pair["krw_earned"]:
                max_krw_pair = pair
                same_krw_list.clear()
                same_krw_list.append(max_krw_pair)
            elif pair["krw_earned"] == max_krw_pair["krw_earned"]:
                same_krw_list.append(pair)

        if len(same_krw_list) > 1:
            # Sort from same_krw_list and convert it into maxcoinunit_same_list
            # 'min_pair' used b/c as small max_coin_unit as possible is better off
            min_coin_pair = None
            same_coin_unit_list = []
            for pair in same_krw_list:
                if min_coin_pair is None:
                    min_coin_pair = pair
                    same_coin_unit_list.append(pair)
                    continue
                if pair["initial_setting"]["max_trading_coin"] < min_coin_pair["initial_setting"]["max_trading_coin"]:
                    min_coin_pair = pair
                    same_coin_unit_list.clear()
                    same_coin_unit_list.append(min_coin_pair)
                elif pair["initial_setting"]["max_trading_coin"] \
                        == min_coin_pair["initial_setting"]["max_trading_coin"]:
                    same_coin_unit_list.append(pair)
            return same_coin_unit_list[0]
        else:
            return same_krw_list[0]


"""Initial Balance optimizer Analyzer"""


class IBOAnalyzer:

    @classmethod
    def get_opt_yield_pair(cls, result: list):
        highest_yield_pair = None
        same_yield_list = []
        for pair in result:
            # first setup
            if highest_yield_pair is None:
                highest_yield_pair = pair
                same_yield_list.append(highest_yield_pair)
                continue

            # compare
            if highest_yield_pair["yield"] < pair["yield"]:
                highest_yield_pair = pair
                same_yield_list.clear()
                same_yield_list.append(highest_yield_pair)
            elif highest_yield_pair["yield"] == pair["yield"]:
                same_yield_list.append(pair)

        # get the best pair within same_yield_list
        if len(same_yield_list) == 1:
            return same_yield_list[0]  # pair 하나 리턴
        elif len(same_yield_list) > 1:
            min_invested_krw_pair = None
            same_invested_krw = []
            for pair in same_yield_list:
                if min_invested_krw_pair is None:
                    min_invested_krw_pair = pair
                    same_invested_krw.append(pair)
                    continue
                if pair["total_krw_invested"] < min_invested_krw_pair["total_krw_invested"]:
                    min_invested_krw_pair = pair
                    same_invested_krw.clear()
                    same_invested_krw.append(pair)
                elif pair["total_krw_invested"] == min_invested_krw_pair["total_krw_invested"]:
                    same_invested_krw.append(pair)
            return same_invested_krw[0]
        else:
            raise Exception("There is no item in same_yield_list!!! Check for solution")


"""Integrated Yield Optimizer Analyzer"""


class IYOAnalyzer:

    @classmethod
    def get_iyo_opt_yield_pair(cls, result: list):
        highest_yield_pair = None
        same_yield_list = []
        for pair in result:
            # first setup
            if highest_yield_pair is None:
                highest_yield_pair = pair
                same_yield_list.append(highest_yield_pair)
                continue

            # compare
            if highest_yield_pair["yield"] < pair["yield"]:
                highest_yield_pair = pair
                same_yield_list.clear()
                same_yield_list.append(highest_yield_pair)
            elif highest_yield_pair["yield"] == pair["yield"]:
                same_yield_list.append(pair)

        # get the best pair within same_yield_list
        if len(same_yield_list) == 1:
            return same_yield_list[0]  # pair 하나 리턴
        elif len(same_yield_list) > 1:
            min_invested_krw_pair = None
            same_exhausted_krw = []
            for pair in same_yield_list:
                if min_invested_krw_pair is None:
                    min_invested_krw_pair = pair
                    same_exhausted_krw.append(pair)
                    continue
                if pair["total_krw_exhausted"] < min_invested_krw_pair["total_krw_exhausted"]:
                    min_invested_krw_pair = pair
                    same_exhausted_krw.clear()
                    same_exhausted_krw.append(pair)
                elif pair["total_krw_exhausted"] == min_invested_krw_pair["total_krw_exhausted"]:
                    same_exhausted_krw.append(pair)
            return same_exhausted_krw[0]
        else:
            raise Exception("There is no item in same_yield_list!!! Check for solution")
