def get_profit_amount(self, buy_idx, sell_idx, buy_depth, sell_depth, buy_fee, sell_fee):
    if self.get_spread(sell_depth["bids"][sell_idx]["price"], sell_fee, buy_depth["asks"][buy_idx]["price"],
                       buy_fee) <= 0:
        return 0, 0

    max_amount_buy = 0
    for i in range(buy_idx + 1):
        max_amount_buy += buy_depth["asks"][i]["amount"]
    max_amount_sell = 0
    for j in range(sell_idx + 1):
        max_amount_sell += sell_depth["bids"][j]["amount"]
    max_amount = min(max_amount_buy, max_amount_sell)

    buy_total = 0
    avg_buyprice = 0
    for i in range(buy_idx + 1):
        price = buy_depth["asks"][i]["price"]
        amount = min(max_amount, buy_total + buy_depth["asks"][i]["amount"]) - buy_total
        if amount <= 0:
            break
        buy_total += amount
        if avg_buyprice == 0 or buy_total == 0:
            avg_buyprice = price
        else:
            avg_buyprice = (avg_buyprice * (buy_total - amount) + price * amount) / buy_total

    sell_total = 0
    avg_sellprice = 0
    for j in range(sell_idx + 1):
        price = sell_depth["bids"][j]["price"]
        amount = min(max_amount, sell_total + sell_depth["bids"][j]["amount"]) - sell_total
        if amount <= 0:
            break
        sell_total += amount
        if avg_sellprice == 0 or sell_total == 0:
            avg_sellprice = price
        else:
            avg_sellprice = (avg_sellprice * (sell_total - amount) + price * amount) / sell_total

    profit = sell_total * avg_sellprice * (1 - sell_fee) - buy_total * avg_buyprice * (1 + buy_fee)
    return profit, max_amount


def get_max_depth_idx(self, buy_depth, sell_depth, buy_fee, sell_fee):
    buy_idx, sell_idx = 0, 0
    while self.get_spread(sell_depth["bids"][0]["price"], sell_fee, buy_depth["asks"][buy_idx]["price"],
                          buy_fee) > 0:
        buy_idx += 1
    while self.get_spread(sell_depth["bids"][sell_idx]["price"], sell_fee, buy_depth["asks"][0]["price"],
                          buy_fee) > 0:
        sell_idx += 1
    return buy_idx, sell_idx


def get_idx_amount(self, buy_depth, sell_depth, buy_fee, sell_fee):
    max_buy_idx, max_sell_idx = self.get_max_depth_idx(buy_depth, sell_depth, buy_fee, sell_fee)
    max_amount = 0
    best_profit = 0
    best_buy_idx, best_sell_idx = 0, 0
    for buy_idx in range(max_buy_idx + 1):
        for sell_idx in range(max_sell_idx + 1):
            profit, amount = self.get_profit_amount(buy_idx, sell_idx, buy_depth, sell_depth, buy_fee, sell_fee)
            if profit >= 0 and profit >= best_profit:
                best_profit = profit
                max_amount = amount
                best_buy_idx, best_sell_idx = buy_idx, sell_idx
    return best_buy_idx, best_sell_idx, max_amount


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
