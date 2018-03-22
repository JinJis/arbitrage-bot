from .market import Market


class Balance:
    def __init__(self, market: Market, balance_dict: dict = None):
        self.market = market
        self._balance_dict = balance_dict

    def update(self, balance_dict: dict):
        self._balance_dict = balance_dict

    def __repr__(self):
        krw_balance = self._balance_dict["krw"]
        eth_balance = self._balance_dict["eth"]

        return "<%s Balance>:\n" \
               "krw { %f available, %f trade_in_use, %f in total }\n" \
               "eth { %f available, %f trade_in_use, %f in total }" % (
                   self.market.value,
                   krw_balance["available"],
                   krw_balance["trade_in_use"],
                   krw_balance["balance"],
                   eth_balance["available"],
                   eth_balance["trade_in_use"],
                   eth_balance["balance"],
               )

    def to_dict(self):
        clone = dict(self._balance_dict)
        clone["market"] = self.market.value
        return clone
