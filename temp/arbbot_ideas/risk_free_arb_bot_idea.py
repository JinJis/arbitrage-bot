class RiskFreeArbBoIdea:
    def __init__(self):
        self.new_spread_count = 0
        self.reverse_spread_count = 0
        # timestep 5번이 지나기 전에 reverse하면 물량 일정하게 유지하면서 청산
        # timestep 5번이 지나면 다시 비율 계산해서 물량 변경후 청산
        self.past_reverse_count = 0
        self.diff = (self.new_spread_count - self.reverse_spread_count)

     # 0, -60으로 설정하면 new : reverse = 약 58:1 비율로 일어난다. reverse에서 
    # 청산 기회가 오면 1/40 비율로 청산, 다 청산할수도 하지 못할 수도 있으나 전부 청산할 가능성이 높다. 
    NEW_SPREAD_THRESHOLD = 0
    REV_SPREAD_THRESHOLD = -60
    
    def is_spread_balance(self, new_spread_orders: list, reverse_spread_orders: list, TRADE_TAG: str, NEW_BIGGER: bool=False):
        # 쏠림 현상을 일단 여기서 고려하지 않고 싶어서 크게 잡음
        DIFF_THRESHOLD = 1000000

        # NEW를 REVERSE보다 DIFF_THRESHOLD만큼 더 실행 가능
        if NEW_BIGGER == True:
            return len(reverse_spread_orders) + DIFF_THRESHOLD > len(new_spread_orders) >= len(reverse_spread_orders)

        # REVERSE와 NEW의 벨런스를 DIFF_THRESHOLD 이하로 유지
        if TRADE_TAG == "NEW":
            return len(reverse_spread_orders) + DIFF_THRESHOLD >= len(new_spread_orders)
        else: 
            return len(new_spread_orders) + DIFF_THRESHOLD >= len(reverse_spread_orders)


    