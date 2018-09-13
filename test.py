import ccxt

bithumb = ccxt.bithumb()
bithumb.apiKey = "6dcbd22b2c31aad9b16a3fa5ed61a468"
bithumb.secret = "ec502fc57d861764032302b21d0b3a15"

print(bithumb.fetch_balance())
