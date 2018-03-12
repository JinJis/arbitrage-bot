from market import Market
import json

class Trader():
    def __init__(self):
        '''
            < 현재 코빗과 코인원 잔고 불러오기 >
            balance = {
                krw: krw 잔고 금액,
                eth: eth 잔고 금액
            }
        '''
        korbit_balance = json.load(open("korbit-balance.json", "r"))
        coinone_balance = json.load(open("coinone-balance.json", "r"))
        self.korbit = Market("Korbit", 0.0008, korbit_balance["krw"], korbit_balance["eth"])
        self.coinone = Market("Coinone", 0.001, coinone_balance["krw"], coinone_balance["eth"])
        
        self.new_spreads = []
        self.new_mov_avg = None
        self.new_sigma = None
        self.new_bolinger_spreads = []
        self.new_bolinger_mov_avg = None
        self.new_bolinger_sigma = None
        
        self.reverse_spreads = []
        self.reverse_mov_avg = None
        self.reverse_sigma = None
        
        
        self.new_stack = []
        self.reverse_stack = []
        
        
        self.clients = {
            "Korbit": self.korbit,
            "Coinone": self.coinone
        }
        
    def total_balance(self, price):
        market_balances = [i.balance_total(price) for i in self.clients.values()]
        return sum(market_balances)

    def total_krw_balance(self):
        return sum([i.krw_balance for i in self.clients.values()])
    
    def total_eth_balance(self):
        return sum([i.eth_balance for i in self.clients.values()])
    
    def get_current_spread(self, long_market, short_market):
        long_hoga = self.get_market_hoga(long_market.name)
        short_hoga = self.get_market_hoga(short_market.name)
        return -long_hoga["maxbid"] * (1 + long_market.fee) + short_hoga["minask"] * (1 - short_market.fee)
    
    def get_market_hoga(self, market_name):
        # hoga = None
        hoga = {
            "minask": 13,
            "maxbid": 11
        }
        if market_name == "Korbit":
            '''
                hoga = {
                    maxbid: value,
                    minask: value
                }
            '''
        if market_name == "Coinone":
            '''
                hoga = {
                    maxbid: value,
                    minask: value
                }
            '''
        return hoga