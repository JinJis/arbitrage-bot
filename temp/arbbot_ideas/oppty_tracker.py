import time
from temp.arbbot_ideas.trade_handler import TradeHandler
from trader.market_manager.market_manager import MarketManager


class OpptyTracker:
    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager, init_rewind_time: int):
        self.target_currency = target_currency
        self.mm1 = mm1
        self.mm2 = mm2
        self.init_rewind_time = init_rewind_time

    def run(self):
        while True:
            TradeHandler(self.target_currency, self.mm1, self.mm2, False, False).launch_inner_outer_ocat()
            time.sleep(self.init_rewind_time)
