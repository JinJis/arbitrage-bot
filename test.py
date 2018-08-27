from config.global_conf import Global
b = Global.get_rfab_combination_list("btc")
a = Global.get_inner_ocat_combination("okcoin", "btc")
print(a)
print(b)