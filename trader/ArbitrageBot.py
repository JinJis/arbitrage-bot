from market import Market
import numpy as np 
import json
import urllib.request
import time
import logging

class ArbitrageBot():
    def __init__(self):
        self.korbit = Market("korbit", fee=0.0008, krw_balance=1000000, eth_balance=10)
        self.coinone = Market("coinone", fee=0.001, krw_balance=1000000, eth_balance=10)
        self.new_spread_stack = np.array([], dtype=np.float32)
        self.reverse_spread_stack = np.array([], dtype=np.float32)
        self.bolinger_spread_stack = np.array([], dtype=np.float32)
        
        self.markets = {
            "korbit": self.korbit,
            "coinone": self.coinone
        }

    def test(self):
        count = 0
        while(count < 100):
            self.execute("coinone", "korbit", 20)
            count += 1

    def execute(self, a_market_name, b_market_name, timestep):
        a_market = self.markets[a_market_name]
        b_market = self.markets[b_market_name]
        
        while (self.new_spread_stack.size < timestep):
            new_spread, reverse_spread, _, _ = self.get_current_spread(a_market_name, b_market_name)
            self.new_spread_stack = np.append(self.new_spread_stack, new_spread)
            self.reverse_spread_stack = np.append(self.reverse_spread_stack, reverse_spread)
            print("loading.. until %s is %s" % (self.new_spread_stack.size, timestep))
            if (self.new_spread_stack.size == timestep):
                print("loading finished\n")
        print("now new stack %s" % self.new_spread_stack)
        print("now reverse stack %s" % self.reverse_spread_stack)
        new_mov_avg = self.new_spread_stack.mean()
        new_sigma = self.new_spread_stack.std()
        reverse_mov_avg = self.reverse_spread_stack.mean()
        reverse_sigma = self.reverse_spread_stack.std()
        
        current_new_spread, current_reverse_spread, hoga_a, hoga_b = self.get_current_spread(a_market_name, b_market_name)
        print("new_mov_avg: %s, new_sigma: %s and current_new: %s" %(new_mov_avg, new_sigma, current_new_spread))
        print("reverse_mov_avg: %s, reverse_sigma: %s and current_reverse: %s" \
              %(reverse_mov_avg, reverse_sigma, current_reverse_spread))
        if (current_new_spread >= new_mov_avg + new_sigma):
            print("[new]")
            a_market.buy(volume=0.03, bid_price=hoga_a["maxbid"])
            b_market.sell(volume=0.03, ask_price=hoga_b["minask"])
        elif (current_reverse_spread >= reverse_mov_avg + reverse_sigma):
            print("[reverse]")
            b_market.buy(volume=0.03, bid_price=hoga_b["maxbid"])
            a_market.sell(volume=0.03, ask_price=hoga_a["minask"])
        else:
            print("[No]")
        total_krw = a_market.balance_total(hoga_a["maxbid"]) + b_market.balance_total(hoga_b["maxbid"])
        print("[Total krw: %s\n" % (total_krw))
        self.new_spread_stack = np.delete(self.new_spread_stack, 0)
        self.reverse_spread_stack = np.delete(self.reverse_spread_stack, 0)
        self.new_spread_stack = np.append(self.new_spread_stack, current_new_spread)
        self.reverse_spread_stack = np.append(self.reverse_spread_stack, current_reverse_spread)
            
    def total_krw_balance(self):
        return sum([i.krw_balance for i in self.markets.values()])
    
    def total_eth_balance(self):
        return sum([i.eth_balance for i in self.markets.values()])
        
    def get_current_spread(self, a_market_name, b_market_name):
        time.sleep(3)
        a_market = self.markets[a_market_name]
        b_market = self.markets[b_market_name]
        a_hoga = self.get_market_hoga(a_market_name)
        b_hoga = self.get_market_hoga(b_market_name)
        print("[%s] maxbid: %s, minask: %s" % (a_market_name, a_hoga["maxbid"], a_hoga["minask"]))
        print("[%s] maxbid: %s, minask: %s" % (b_market_name, b_hoga["maxbid"], b_hoga["minask"]))
        new_spread = self.get_spread(a_hoga["maxbid"], a_market.fee, b_hoga["minask"], b_market.fee)
        reverse_spread = self.get_spread(b_hoga["maxbid"], b_market.fee, a_hoga["minask"], a_market.fee)
        return new_spread, reverse_spread, a_hoga, b_hoga
    
    def get_spread(self, maxbid, maxbid_fee, minask, minask_fee): 
        return -maxbid * (1 + maxbid_fee) + minask * (1 - minask_fee)
    
    def get_market_hoga(self, market_name, currency="eth_krw"):
        hoga = None
        if market_name == "korbit":
            depth = self.get_depth_api("https://api.korbit.co.kr/v1/orderbook?currency_pair=%s" % currency)
            depth_asks = depth["asks"]
            depth_bids = depth["bids"]
            hoga = { "minask": np.array(depth_asks)[:,0].astype(int).min(),\
                    "maxbid": np.array(depth_bids)[:,0].astype(int).max() }
        if market_name == "coinone":
            currency = "eth"
            depth = self.get_depth_api("https://api.coinone.co.kr/orderbook?currency=%s" % currency)
            hoga = { "minask": np.array([ask["price"] for ask in depth["ask"]]).astype(int).min(), \
                    "maxbid": np.array([bid["price"] for bid in depth["bid"]]).astype(int).max() }
        return hoga
    
    def get_depth_api(self, url):
        req = urllib.request.Request(url, None, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent": "curl"})
        res = urllib.request.urlopen(req)
        if (res == None):
            return None
        depth = json.loads(res.read().decode('utf8'))
        return depth

t = ArbitrageBot()
t.test()