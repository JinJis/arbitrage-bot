from config.global_conf import Global

hello = Global.get_rfab_combination_list("tron")
for i in hello:
    print(type(i[0]), type(i[1]))
