import logging
import json 

class Market(object):
    def __init__(self, name, fee=0, krw_balance=3000., eth_balance=10., persistent=True):
        self.name = name
        self.filename = name + "-balance.json"
        self.krw_balance = krw_balance
        self.eth_balance = eth_balance
        self.fee = fee
        self.persistent = persistent
        if self.persistent:
            try:
                self.load()
            except IOError:
                pass

    def buy(self, volume, bid_price):
        logging.info("execute buy %f ETH @ %f on %s" % (volume, bid_price, self.name))
        self.krw_balance -= bid_price * volume
        self.btc_balance += volume - volume * self.fee
        if self.persistent:
            # db 사용하면 여기다가 insert
            self.save()
        
    def sell(self, volume, ask_price):
        logging.info("execute sell %f ETH @ %f on %s" % (volume, ask_price, self.name))
        self.eth_balance -= volume
        self.krw_balance += ask_price * volume - ask_price * volume * self.fee
        if self.persistent:
            self.save()

    def load(self):
        # db select
        data = json.load(open(self.filename, "r"))
        self.krw_balance = data["krw"]
        self.btc_balance = data["eth"]

    def save(self):
        # db insert
        data = {'krw': self.krw_balance, 'eth': self.eth_balance}
        json.dump(data, open(self.filename, "w"))

    def balance_total(self, price):
        return self.krw_balance + self.eth_balance * price