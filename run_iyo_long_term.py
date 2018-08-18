import logging
import itertools as it
from config.global_conf import Global
from config.trade_setting_config import TradeSettingConfig
from config.shared_mongo_client import SharedMongoClient
from optimizer.arbitrage_combination_optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer


def main(coin_name: str, init_time: str, final_time: str):
    Global.configure_default_root_logging(should_log_to_file=False, log_level=logging.INFO)
    SharedMongoClient.initialize(should_use_localhost_db=False)
    db_client = SharedMongoClient.instance()

    time_list = make_time_list(init_time, final_time)

    prev_time = None
    for cur_time in time_list:
        if prev_time is None:
            prev_time = cur_time
            continue
        logging.warning("Nohup conducting -> start_time: %s, end_time: %s" % (prev_time, cur_time))
        # Global.send_to_slack_channel("IYO Initiated!! start_time: %s, end_time: %s" % (prev_time, cur_time))

        start_time = Global.convert_local_datetime_to_epoch(prev_time, timezone="kr")
        end_time = Global.convert_local_datetime_to_epoch(cur_time, timezone="kr")

        # draw iyo_config for bal & factor_setting
        iyo_config = Global.read_iyo_setting_config(coin_name)

        # FIXME: 빗썸 등등 거래소 생긴 날부터는 밑에 주석 쓰기
        # rfab_combi_list = Global.get_rfab_combination_list(coin_name)
        rfab_combi_list = list(it.combinations(["okcoin", "coinnest"], 2))
        for _combi in rfab_combi_list:
            logging.critical("[%s-%s-%s] IYO conducting -> start_time: %s, end_time: %s" % (
                coin_name.upper(), str(_combi[0]).upper(), str(_combi[1]).upper(), start_time, end_time))

            # set settings, bal_fact_settings, factor_settings
            settings = TradeSettingConfig.get_settings(mm1=_combi[0],
                                                       mm2=_combi[1],
                                                       target_currency=coin_name,
                                                       start_time=start_time, end_time=end_time,
                                                       division=iyo_config["division"],
                                                       depth=iyo_config["depth"],
                                                       consecution_time=iyo_config["consecution_time"],
                                                       is_virtual_mm=True)

            bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(iyo_config["krw_seq_end"])

            factor_settings = TradeSettingConfig.get_factor_settings(iyo_config["max_trade_coin_end"],
                                                                     iyo_config["threshold_end"],
                                                                     iyo_config["factor_end"],
                                                                     iyo_config["appx_unit_coin_price"])

            iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings)

            # finally save to mongoDB
            if len(iyo_result) > 0:
                db_client["statistics"]["iyo"].insert_many(iyo_result)
            else:
                logging.critical("There was no oppty!! Skipping to next combination!")
                continue
            logging.warning("Nohup done, now conducting next time set!!")
            prev_time = cur_time


def make_time_list(init_time: str, final_time: str):
    cur_time = init_time
    time_list = [init_time]
    while int(cur_time[8:10]) <= int(final_time[8:10]):
        cur_time_day = cur_time[8:10]
        if int(cur_time_day) < 9:
            next_time_day = ("0%d" % (int(cur_time_day) + 1))
        else:
            next_time_day = str(int(cur_time_day) + 1)
        cur_time = cur_time[:8] + next_time_day + cur_time[10:]
        time_list.append(cur_time)
    return time_list


if __name__ == '__main__':

    # for more than one month dur
    s_time = '2018.08.16 09:00:00'
    e_time = '2018.08.16 20:00:00'

    for target_currency in ["eth"]:
        main(target_currency, s_time, e_time)
    # Global.send_to_slack_channel("IYO for past date set done for all COMBINATION!! ")
