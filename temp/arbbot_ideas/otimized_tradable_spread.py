from analyzer.analyzer import BasicAnalyzer

"""OTS Strategy analyzer"""


class OTSAanlyzer:
    # Final ready-to-be-applied static function of "OTS strategy"
    @staticmethod
    def optimized_tradable_spread_strategy(mm1_orderbook: dict, mm2_orderbook: dict,
                                           mm1_market_fee: float, mm2_market_fee: float,
                                           max_ob_index_num: int, max_coin_trading_unit: float = None):
        mm1_asks_dict_sorted, mm1_bids_dict_sorted = \
            OTSAanlyzer.get_price_amount_dict_sorted(mm1_orderbook, max_ob_index_num)

        mm2_asks_dict_sorted, mm2_bids_dict_sorted = \
            OTSAanlyzer.get_price_amount_dict_sorted(mm2_orderbook, max_ob_index_num)

        # new => buy in mm1, sell in mm2
        (opt_new_spread, opt_new_mm1_buy_price, opt_new_mm1_buy_index, opt_new_mm2_sell_price, opt_new_mm2_sell_index,
         opt_new_trading_qty, new_spread_in_unit, new_avail_mm1_qty, new_avail_mm2_qty) = \
            OTSAanlyzer.get_optimized_spread_infos(mm1_asks_dict_sorted, mm1_market_fee,
                                                   mm2_bids_dict_sorted, mm2_market_fee,
                                                   max_ob_index_num, max_coin_trading_unit)

        # rev => buy in mm2, sell in mm1
        (opt_rev_spread, opt_rev_mm2_buy_price, opt_rev_mm2_buy_index, opt_rev_mm1_sell_price, opt_rev_mm1_sell_index,
         opt_rev_trading_qty, rev_spread_in_unit, rev_avail_mm1_qty, rev_avail_mm2_qty) = \
            OTSAanlyzer.get_optimized_spread_infos(mm2_asks_dict_sorted, mm2_market_fee,
                                                   mm1_bids_dict_sorted, mm1_market_fee,
                                                   max_ob_index_num, max_coin_trading_unit)

        return (new_spread_in_unit, rev_spread_in_unit, opt_new_spread, opt_rev_spread,
                opt_new_mm1_buy_price, opt_new_mm1_buy_index,
                opt_new_mm2_sell_price, opt_new_mm2_sell_index, opt_new_trading_qty,
                opt_rev_mm2_buy_price, opt_rev_mm2_buy_index,
                opt_rev_mm1_sell_price, opt_rev_mm1_sell_index, opt_rev_trading_qty,
                new_avail_mm1_qty, new_avail_mm2_qty, rev_avail_mm1_qty, rev_avail_mm2_qty)

    @staticmethod
    def get_optimized_spread_infos(buy_dict: dict, buy_fee: float,
                                   sell_dict: dict, sell_fee: float,
                                   ob_index_num: int, max_trading_unit: float):

        spread_set = list()
        for i in range(0, ob_index_num):
            buy_price = int(buy_dict["price"][i].to_decimal())
            for k in range(0, ob_index_num):
                sell_price = int(sell_dict["price"][k].to_decimal())

                # since we have to trade the same amount at buy and sell side, as well as complying with each market
                # amounts and max_trading_unit
                buy_dict_amount = float(buy_dict["amount"][i].to_decimal())
                sell_dict_amount = float(sell_dict["amount"][k].to_decimal())
                possible_trading_qty = float(min(buy_dict_amount * (1 - buy_fee), sell_dict_amount, max_trading_unit))
                if possible_trading_qty < 0:
                    possible_trading_qty = 0

                # actual spread and append to spread list
                spread_in_unit = (-1) * buy_price / (1 - buy_fee) + (+1) * sell_price * (1 - sell_fee)
                spread_for_trade = spread_in_unit * possible_trading_qty
                spread_set.append((spread_for_trade, i, k, possible_trading_qty, spread_in_unit))

        # get the maximized pair for trading
        (opt_spread, opt_buy_index,
         opt_sell_index, opt_trading_qty, opt_spread_in_unit) = OTSAanlyzer.get_max_pair_infos(spread_set)

        opt_buy_price = int(buy_dict["price"][opt_buy_index].to_decimal())
        opt_sell_price = int(sell_dict["price"][opt_sell_index].to_decimal())
        avail_buy_amount = float(buy_dict["amount"][opt_buy_index].to_decimal())
        avail_sell_amount = float((sell_dict["amount"][opt_sell_index].to_decimal()))

        return (opt_spread, opt_buy_price, opt_buy_index,
                opt_sell_price, opt_sell_index, opt_trading_qty, opt_spread_in_unit, avail_buy_amount,
                avail_sell_amount)

    @staticmethod
    def get_max_pair_infos(spread_set: list):
        max_pair = None
        for pair in spread_set:
            # 초기값 설정
            if max_pair is None:
                max_pair = pair
                continue
            # 비교
            elif pair[0] > max_pair[0]:
                max_pair = pair
            else:
                continue

        # return opt_spread for trade, opt_buy_index, opt_sell_index, opt_trading_qty, spread in one unit
        return max_pair[0], max_pair[1], max_pair[2], max_pair[3], max_pair[4]

    @staticmethod
    def get_price_amount_dict_sorted(orderbook: dict, index: int):
        return dict(price=list(orderbook["asks"][i]["price"] for i in range(0, index)),
                    amount=list(orderbook["asks"][i]["amount"] for i in range(0, index))), \
               dict(price=list(orderbook["bids"][i]["price"] for i in range(0, index)),
                    amount=list(orderbook["bids"][i]["amount"] for i in range(0, index)))
