class FilledOrderAnalyzer:
    @staticmethod
    def get_filled_orders_within(prev_filled_orders, curr_filled_orders):
        return curr_filled_orders[:curr_filled_orders.index(prev_filled_orders[0])]

    @staticmethod
    def check_order_type_from_orderbook(prev_orderbook, curr_filled_orders):
        # convert from bson decimal128 to python decimal for calculation
        min_ask_price = prev_orderbook["asks"][0].price.to_decimal()
        max_bid_price = prev_orderbook["bids"][0].price.to_decimal()

        result = list()

        for filled_order in curr_filled_orders:
            # get price of filled order
            filled_order_price = filled_order.price.to_decimal()

            # get diff
            min_ask_diff = abs(min_ask_price - filled_order_price)
            max_bid_diff = abs(max_bid_price - filled_order_price)

            # get nearest type of order
            if min_ask_diff < max_bid_diff:
                result.append("ask")
            elif min_ask_diff == max_bid_diff:
                result.append("both")
            else:
                result.append("bid")

        return result
