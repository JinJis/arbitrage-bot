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
        self.new_stack = []
        self.reverse_stack = []
        self.markets = {
            "korbit": self.korbit,
            "coinone": self.coinone
        }
        
    def execute(self, a_market_name, b_market_name):
        new_spreads = self.get_spreads(a_market_name, b_market_name)
        reverse_spreads = self.get_spreads(b_market_name, a_market_name)
        new_mov_avg = new_spreads.mean()
        new_sigma = new_spreads.std()
        reverse_mov_avg = reverse_spreads.mean()
        reverse_sigma = reverse_spreads.std()
        current_new_spread, current_reverse_spread = self.get_current_spread(a_market_name, b_market_name)
        
        if (current_new_spread >= new_mov_avg + new_sigma):
            print("%s buy, %s sell" % (a_market_name, b_market_name))
            print("%s buy, %s sell" % (b_market_name, a_market_name))
        elif (current_reverse_spread >= reverse_mov_avg + reverse_sigma):
            print("%s buy, %s sell" % (b_market_name, a_market_name))
            print("%s buy, %s sell" % (a_market_name, b_market_name))
        else:
            print("No!")
        
        
    def total_balance(self, price):
        market_balances = [i.balance_total(price) for i in self.markets.values()]
        return sum(market_balances)

    def total_krw_balance(self):
        return sum([i.krw_balance for i in self.markets.values()])
    
    def total_eth_balance(self):
        return sum([i.eth_balance for i in self.markets.values()])
    
    def get_spreads(self, long_market_name, short_market_name, value_count=20):
        long_market = self.markets[long_market_name]
        short_market = self.markets[short_market_name]
        long_hoga = open("./testdata/%s-hoga.json" % long_market_name, 'r')
        short_hoga = open("./testdata/%s-hoga.json" % short_market_name, 'r')
        long_hoga = list(map(lambda x: json.loads(x), long_hoga.read().split()))
        short_hoga = list(map(lambda x: json.loads(x), short_hoga.read().split()))
        
        long_hoga = np.array([hoga["maxBid_price"] for hoga in long_hoga])
        short_hoga = np.array([hoga["minAsk_price"] for hoga in short_hoga])
        return -(long_hoga[-value_count:]) * (1 + long_market.fee) \
                 + (short_hoga[-value_count:] * (1 - short_market.fee))
        
    def get_spread(self, maxbid, maxbid_fee, minask, minask_fee): 
        return -maxbid * (1 + maxbid_fee) + minask * (1 - minask_fee)
    
    def get_current_spread(self, a_market_name, b_market_name):
        a_market = self.markets[a_market_name]
        b_market = self.markets[b_market_name]
        a_hoga = self.get_market_hoga(a_market_name)
        b_hoga = self.get_market_hoga(b_market_name)
        new_spread = self.get_spread(a_hoga["maxbid"], a_market.fee, b_hoga["minask"], b_market.fee)
        reverse_spread = self.get_spread(b_hoga["maxbid"], b_market.fee, a_hoga["minask"], a_market.fee)
        return new_spread, reverse_spread
    
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
    
    def get_market_hoga(self, market_name, currency="eth_krw"):
        hoga = None
        if market_name == "korbit":
            depth = self.get_depth_api("https://api.korbit.co.kr/v1/orderbook?currency_pair=%s" % currency)
            depth_asks = depth["asks"]
            depth_bids = depth["bids"]
            hoga = { "minask": np.array(depth_asks)[:,0].astype(int).min(),\
                    "maxbid": np.array(depth_bids)[:,0].astype(int).max() }
        if market_name == "coinone":
            depth = self.get_depth_api("https://api.coinone.co.kr/orderbook?currency=%s" % currency)
            hoga = { "minask": np.array([ask["price"] for ask in depth["ask"]]).astype(int).min(), \
                    "maxbid": np.array([bid["price"] for bid in depth["bid"]]).astype(int).max() }
        return hoga