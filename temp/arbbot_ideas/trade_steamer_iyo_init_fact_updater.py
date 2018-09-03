"""처음에 outer OCAT할때"""
# update rest of IYO config
# first find specific ocat_result_dict by trading combination
target_ocat = None
for ocat in self.ocat_final_result:
    if ocat["combination"] == "%s-%s-%s" % (self.target_currency.upper(),
                                            self.mm1_name.upper(), self.mm2_name.upper()):
        target_ocat = ocat
        break

if target_ocat is None:
    raise Exception("There is no detected combination for IYO_config update!!")

# update iyo_config
self.update_iyo_config_by_regular_otc(target_ocat=target_ocat)

""" 이거는 EXhaust Stage 설정할때 들어갔던거"""
# when exhaust ctrl stage increments, update IYO config by real time mkt condition
iyo_config = Global.read_iyo_setting_config(self.target_currency)
settings = TradeSettingConfig.get_settings(mm1_name=self.mm1_name,
                                           mm2_name=self.mm2_name,
                                           target_currency=self.target_currency,
                                           start_time=self.bot_start_time,
                                           end_time=now_time,
                                           division=iyo_config["division"],
                                           depth=iyo_config["depth"],
                                           consecution_time=iyo_config["consecution_time"],
                                           is_virtual_mm=True)

ocat_result = OpptyTimeCollector.run(settings)

self.update_iyo_config_by_regular_otc(target_ocat=ocat_result)

""" 통합으로 뽑아내는거 """


def update_iyo_config_by_regular_otc(self, target_ocat: dict):
    max_trade_coin_end = round(
        float(max(self.mm1_coin_bal, self.mm2_coin_bal) / self.MAX_TRADING_COIN_DIVISION), 4)
    threshold_end = int(max(
        target_ocat["new_max_unit_spread"], target_ocat["rev_max_unit_spread"]) * max_trade_coin_end)
    appx_unit_coin_price = int(max(target_ocat["avg_new_mid_price"], target_ocat["avg_rev_mid_price"]))

    Global.write_iyo_config_by_target_currency(self.target_currency,
                                               max_trade_coin_end * self.IYO_INIT_FACT_SET_MULTIPLIER,
                                               threshold_end * self.IYO_INIT_FACT_SET_MULTIPLIER,
                                               appx_unit_coin_price)
