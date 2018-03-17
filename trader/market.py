import numpy as np
import logging
import os
import glob
import re 
import sys
import json

class Market(object):
    def __init__(self, name, fee=0, krw_balance=3000., eth_balance=10., persistent=False):
        self.name = name
        self.filename = "./testdata/%s-balance.json" % name
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
        print("execute buy %f ETH @ %f on %s" % (volume, bid_price, self.name))
        self.eth_balance += volume - volume * self.fee
        self.krw_balance -= bid_price * volume
        if self.persistent:
            self.save()
        
    def sell(self, volume, ask_price):
        print("execute sell %f ETH @ %f on %s" % (volume, ask_price, self.name))
        self.eth_balance -= volume
        self.krw_balance += ask_price * volume - ask_price * volume * self.fee
        if self.persistent:
            self.save()

    def load(self):
        # db select
        data = json.load(open(self.filename, "r"))
        self.krw_balance = data["krw"]
        self.eth_balance = data["eth"]

    def save(self):
        # db insert
        data = {'krw': self.krw_balance, 'eth': self.eth_balance}
        json.dump(data, open(self.filename, "w"))

    def balance_total(self, price):
        return self.krw_balance + self.eth_balance * price