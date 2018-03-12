from market import Market
import numpy as np 
import json

class ArbitrageBot():
    def __init__(self):
        '''
            < 현재 코빗과 코인원 잔고 불러오기 >
            balance = {
                krw: krw 잔고 금액,
                eth: eth 잔고 금액
            }
        '''
        self.korbit = Market("Korbit", 0.0008)
        self.coinone = Market("Coinone", 0.001)
#         self.new_spreads = get_spreads
#         self.new_mov_avg = None
#         self.new_sigma = None
#         self.new_bolinger_spreads = []
#         self.new_bolinger_mov_avg = None
        
#         self.reverse_spreads = []
#         self.reverse_mov_avg = None
#         self.reverse_sigma = None
#         self.reverse_bolinger_spreads = []
#         self.reverse_bolinger_mov_avg = None
        
        self.new_stack = []
        self.reverse_stack = []
        
        
        self.clients = {
            "korbit": self.korbit,
            "coinone": self.coinone
        }
        
    def run(self, a_market_name, b_market_name):
        new_spreads = get_spreads(a_market_name, b_market_name)
        reverse_spreads = get_spreads(b_market_name, a_market_name)
        new_mov_avg = new_spreads.mean()
        new_sigma = new_spreads.std()
        reverse_mov_avg = reverse_spreads.mean()
        reverse_sigma = reverse_spreads.std()
        current_new_spread, current_reverse_spread = get_current_spread()
        
        if (current_new_spread >= new_mov_avg + new_sigma):
            # long, short execute
        if (current_reverse_spread >= reverse_mov_avg + reverse_sigma):
            # short long execute
        
        # no
        
    def total_balance(self, price):
        market_balances = [i.balance_total(price) for i in self.clients.values()]
        return sum(market_balances)

    def total_krw_balance(self):
        return sum([i.krw_balance for i in self.clients.values()])
    
    def total_eth_balance(self):
        return sum([i.eth_balance for i in self.clients.values()])
    
    def get_spreads(self, long_market_name, short_market_name, value_count=20):
        long_market = self.clients[long_market_name]
        short_market = self.clients[short_market_name]
        long_hoga = open("./testdata/" + long_market_name + "-hoga.json", 'r')
        short_hoga = open("./testdata/" + short_market_name + "-hoga.json", 'r')
        long_hoga = list(map(lambda x: json.loads(x), long_hoga.read().split()))
        short_hoga = list(map(lambda x: json.loads(x), short_hoga.read().split()))
        
        long_hoga = np.array([hoga["maxBid_price"] for hoga in long_hoga])
        short_hoga = np.array([hoga["minAsk_price"] for hoga in short_hoga])
        return -(long_hoga[-value_count:]) * (1 + long_market.fee) \
                 + (short_hoga[-value_count:] * (1 - short_market.fee))
        
    def get_spread(maxbid, maxbid_fee, minask, minask_fee): 
        return -maxbid * (1 + maxbid_fee) + minask * (1 - minask_fee)
    
    def get_current_spread(self, a_market, b_market):
        a_hoga = self.get_market_hoga(a_market.name)
        b_hoga = self.get_market_hoga(b_market.name)
        new_spread = get_spread(a_hoga["maxbid"], a_market.fee, b_hoga["minask"], b_market.fee)
        reverse_spread = get_spread(b_hoga["maxbid"], b_market.fee, a_hoga["minask"], a_market.fee)
        return new_spread, reverse_spread
    
    def get_market_hoga(self, market_name):
        hoga = None
        if market_name == "korbit":
            hoga = {
                "maxbid": value,
                "minask": value
                }
        if market_name == "coinone":
            hoga = {
                "maxbid": value,
                "minask": value
            }
        return hoga