from enum import Enum
from bson import Decimal128


class OrderType(Enum):
    LIMIT_BUY = "limit_buy"
    LIMIT_SELL = "limit_sell"
    MARKET_BUY = "market_buy"
    MARKET_SELL = "market_sell"


class Market(Enum):
    VIRTUAL = "virtual"
    COINONE = "coinone"
    KORBIT = "korbit"


class Order:
    def __init__(self, market: Market, order_type: OrderType, order_id: str, price: int, amount: float):
        self.market = market
        self.order_type = order_type
        self.order_id = order_id
        self.price = price
        self.amount = amount

        # TODO: request for filled orders until the order is completely filled
        self.is_filled = False
        self.filled_orders = list()

    def update(self):
        if self.market == Market.VIRTUAL:
            self.update_virtual()
        elif self.market == Market.COINONE:
            self.update_coinone()
        elif self.market == Market.KORBIT:
            self.update_korbit()
        else:
            raise ValueError("No such market: %s" % self.market)

    def update_virtual(self):
        pass

    def update_coinone(self):
        pass

    def update_korbit(self):
        pass

    def to_dict(self):
        return {
            "market": self.market.value,
            "order": self.order_type.value,
            "order_id": self.order_id,
            "price": Decimal128(self.price),
            "amount": Decimal128(self.amount)
        }
