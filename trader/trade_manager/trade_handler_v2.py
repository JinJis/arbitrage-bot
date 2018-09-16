import sys
import time
import pymongo
import logging
from itertools import groupby
from config.global_conf import Global
from analyzer.trade_analyzer import MCTSAnalyzer, BasicAnalyzer
from collector.oppty_time_collector import OpptyTimeCollector
from collector.scheduler.otc_scheduler import OTCScheduler
from config.config_market_manager import ConfigMarketManager
from config.shared_mongo_client import SharedMongoClient
from config.trade_setting_config import TradeSettingConfig
from trader.market_manager.market_manager import MarketManager


class TradeHandlerV2:
    MIN_TRDBLE_COIN_MLTPLIER = None
    TIME_DUR_OF_SETTLEMENT = None
    TRADING_MODE_LOOP_INTERVAL = 5

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager):

        # steamer init relevant
        self.streamer_db = SharedMongoClient.get_streamer_db()
        self.is_initiation_mode = True
        self.is_trading_mode = False

        # MARKET relevant
        self.mm1 = mm1
        self.mm2 = mm2
        self.target_currency = target_currency
        self.mm1_name = self.mm1.get_market_name().lower()
        self.mm2_name = self.mm2.get_market_name().lower()
        self.mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
        self.mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
        self.mm1_coin_bal = float(self.mm1.balance.get_available_coin(target_currency))
        self.mm2_coin_bal = float(self.mm2.balance.get_available_coin(target_currency))
        self.target_settings = None

        # MTCU relevant
        self.mm1_ob = None
        self.mm2_ob = None
        self.trade_type = None
        self.streamer_min_trading_coin = None
        self.past_spread_to_trade_list = list()
        self.present_spread_to_trade_list = list()
        self.mctu_spread_threshold = None
        self.mctu_royal_spread = None
        self.is_royal_spread = False
        self.is_oppty = False

        # TIME relevant
        self.streamer_start_time = int(time.time())
        self.ocat_rewind_time = None
        self._bot_start_time = None
        self._settlement_time = None
        self.trading_mode_now_time = None

        # EXHAUSTION relevant
        self.revenue_ledger = dict()
        self.is_time_flow_above_exhaust = True
        self.settlment_reached = False

    """
    ==========================
    || INITIATION MODE ONLY ||
    ==========================
    """

    def set_initial_trade_setting(self):
        self.MIN_TRDBLE_COIN_MLTPLIER = float(input("Please indicate Min Tradable Coin Multiplier (gte 1.0) "))
        settle_hour = int(input("Please indicate settlement hour (int only)"))
        settle_min = int(input("Please indicate settlement minute (int only)"))
        self.TIME_DUR_OF_SETTLEMENT = settle_hour * 60 * 60 + settle_min * 60
        self.ocat_rewind_time = int(self.streamer_start_time - self.TIME_DUR_OF_SETTLEMENT)

    def launch_inner_outer_ocat(self):
        # run Inner OCAT
        # decide which market has the most coin and make it as a set point
        if self.mm1_coin_bal > self.mm2_coin_bal:
            set_point_market = self.mm1_name
        elif self.mm1_coin_bal < self.mm2_coin_bal:
            set_point_market = self.mm2_name
        else:
            logging.critical("Coin Balances for both are market same. Plz manually transfer coin")
            set_point_market = str(input("Manual coin transfer done, set_point_market is:"))
        self.run_inner_or_outer_ocat(set_point_market, self.target_currency, is_inner_ocat=True)

        # run Outer OCAT
        self.run_inner_or_outer_ocat(set_point_market, self.target_currency, is_inner_ocat=False)

        logging.warning("Inner & Outer OCAT finished.")

    def run_inner_or_outer_ocat(self, set_point_market: str, target_currency: str, is_inner_ocat: bool):
        if is_inner_ocat:
            # create combination of coin that is injected by validating if the exchange has that coin
            logging.critical("Set Point Market is: [%s]" % set_point_market.upper())
            inner_ocat_list = Global.get_inner_ocat_combination(set_point_market, target_currency)
            logging.critical("--------Conducting Inner OCAT--------")
            ocat_final_result = self.otc_all_combination_by_one_coin(target_currency, inner_ocat_list)

        elif not is_inner_ocat:
            logging.critical("--------Conducting Outer OCAT--------")
            ocat_final_result = []
            for outer_ocat_coin in list(Global.read_avail_coin_in_list()):
                logging.warning("Now conducting [%s]" % outer_ocat_coin.upper())
                outer_ocat_list = Global.get_rfab_combination_list(outer_ocat_coin)
                ocat_result = self.otc_all_combination_by_one_coin(outer_ocat_coin, outer_ocat_list)
                ocat_final_result.extend(ocat_result)

        else:
            raise Exception("Please indicate if it is Inner OCAT or not")

        descending_order_result = OTCScheduler.sort_by_logest_oppty_time_to_lowest(ocat_final_result)
        top_ten_descend_order_result = descending_order_result[:10]

        for result in top_ten_descend_order_result:
            new_percent = (result["new"] / self.TIME_DUR_OF_SETTLEMENT) * 100
            rev_percent = (result["rev"] / self.TIME_DUR_OF_SETTLEMENT) * 100
            new_spread_strength = result["new_spread_ratio"] * 100
            rev_spread_strength = result["rev_spread_ratio"] * 100

            logging.warning("[%s] NEW: %.2f%%, REV: %.2f%% // NEW_SPREAD_STRENGTH: %.2f%%, REV_SPREAD_STRENGTH: %.2f%%"
                            % (result["combination"], new_percent, rev_percent,
                               new_spread_strength, rev_spread_strength))

    def otc_all_combination_by_one_coin(self, target_currency: str, combination_list: list):
        all_ocat_result_by_one_coin = []
        for _combi in combination_list:
            # draw iyo_config for settings
            iyo_config = Global.read_iyo_setting_config(target_currency)

            settings = TradeSettingConfig.get_settings(mm1_name=_combi[0],
                                                       mm2_name=_combi[1],
                                                       target_currency=target_currency,
                                                       start_time=self.ocat_rewind_time,
                                                       end_time=self.streamer_start_time,
                                                       division=iyo_config["division"],
                                                       depth=iyo_config["depth"],
                                                       consecution_time=iyo_config["consecution_time"],
                                                       is_virtual_mm=True)

            try:
                otc_result_dict = OpptyTimeCollector.run(settings=settings)
                total_dur_dict = OpptyTimeCollector.get_total_duration_time(otc_result_dict)
                total_dur_dict["new_spread_ratio"] = otc_result_dict["new_spread_ratio"]
                total_dur_dict["rev_spread_ratio"] = otc_result_dict["rev_spread_ratio"]
                total_dur_dict["new_max_unit_spread"] = otc_result_dict["new_max_unit_spread"]
                total_dur_dict["rev_max_unit_spread"] = otc_result_dict["rev_max_unit_spread"]
                total_dur_dict["combination"] = \
                    "%s-%s-%s" % (target_currency.upper(), str(_combi[0]).upper(), str(_combi[1]).upper())
                all_ocat_result_by_one_coin.append(total_dur_dict)

            except TypeError as e:
                logging.error("Something went wrong in OTC scheduler", e)
                continue

        return all_ocat_result_by_one_coin

    def to_proceed_handler_for_initiation_mode(self):

        to_proceed = str(input("Do you want to change any market settings? (Y/n)"))
        if to_proceed == "Y":

            # set settings accordingly
            self.target_currency = str(input("Insert Target Currency: "))
            self.mm1: MarketManager = getattr(ConfigMarketManager, input("Insert mm1: ").upper()).value
            self.mm2: MarketManager = getattr(ConfigMarketManager, input("Insert mm2: ").upper()).value
            self.mm1_name = self.mm1.get_market_name().lower()
            self.mm2_name = self.mm2.get_market_name().lower()

        elif to_proceed == "n":
            pass

        else:
            logging.error("Irrelevant command. Please try again")
            return self.to_proceed_handler_for_initiation_mode()

        # update trading env setting

        # update streamer_min_trading_coin
        self.streamer_min_trading_coin \
            = max(Global.read_min_trading_coin(self.mm1_name, self.target_currency),
                  Global.read_min_trading_coin(self.mm2_name, self.target_currency)) * self.MIN_TRDBLE_COIN_MLTPLIER

        # set trade strategy
        self.trade_type = str(input("Insert Trade Strategy (new/rev): "))

        logging.warning("================ [INITIAL BALANCE] ================")
        logging.warning("[%s Balance] >> KRW: %f, %s: %f" % (self.mm1_name.upper(), self.mm1_krw_bal,
                                                             self.target_currency.upper(),
                                                             self.mm1_coin_bal))
        logging.warning("[%s Balance] >> KRW: %f, %s: %f\n" % (self.mm2_name.upper(), self.mm2_krw_bal,
                                                               self.target_currency.upper(),
                                                               self.mm2_coin_bal))
        logging.warning("Now initiating with typed settings!!")
        return True

    def get_min_tradable_coin_unit_spread_list_init_mode(self, anal_start_time: int, anal_end_time: int):

        # get OTC from determined combination
        otc_result_dict = self.get_otc_result_init_mode(anal_start_time, anal_end_time)

        # get mm1, mm2 collection by target_currency
        mm1_col = getattr(SharedMongoClient, "get_%s_db" % self.mm1_name)()[self.target_currency + "_orderbook"]
        mm2_col = getattr(SharedMongoClient, "get_%s_db" % self.mm2_name)()[self.target_currency + "_orderbook"]

        # loop through sliced_oppty_dur and launch backtesting
        min_trdble_coin_unit_sprd_list = []
        for sliced_time_list in otc_result_dict[self.trade_type]:
            start_time = sliced_time_list[0]
            end_time = sliced_time_list[1]

            mm1_cursor, mm2_cursor = SharedMongoClient.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

            for mm1_data, mm2_data in zip(mm1_cursor, mm2_cursor):
                spread_info_dict = MCTSAnalyzer.min_coin_tradable_spread_strategy(mm1_data, mm2_data,
                                                                                  self.mm1.taker_fee,
                                                                                  self.mm2.taker_fee,
                                                                                  self.streamer_min_trading_coin)

                target_spread_info = spread_info_dict[self.trade_type]
                if (target_spread_info.able_to_trade is False) or (target_spread_info.spread_to_trade < 0):
                    continue
                min_trdble_coin_unit_sprd_list.append(target_spread_info)

        current_spread_to_trade_list = [{"spread_to_trade": spread_info.spread_to_trade,
                                         "sell_amt": spread_info.sell_order_amt,
                                         "buy_amt": spread_info.buy_order_amt}
                                        for spread_info in min_trdble_coin_unit_sprd_list]

        # if there is no Oppty,
        if len(current_spread_to_trade_list) == 0:
            logging.error("[WARNING] There is no oppty.. Waiting\n")
            return

        # get spread_to_trade list from min_trdble_coin_sprd_list
        self.past_spread_to_trade_list.extend(current_spread_to_trade_list)

    def log_past_mctu_info(self):
        local_anal_st = Global.convert_epoch_to_local_datetime(self.ocat_rewind_time, timezone="kr")
        local_anal_et = Global.convert_epoch_to_local_datetime(self.streamer_start_time, timezone="kr")

        logging.warning("=========== [MCTU INFO] ==========")
        logging.warning("[Anal Duration]: %s - %s" % (local_anal_st, local_anal_et))
        logging.warning("\n[SPREAD RECORDER]:\n%s" % self.get_mctu_spread_and_frequency(self.past_spread_to_trade_list))

    def set_time_relevant_before_trading_mode(self):
        self.trading_mode_now_time = int(time.time())
        self._bot_start_time = self.trading_mode_now_time
        self._settlement_time = self._bot_start_time + self.TIME_DUR_OF_SETTLEMENT

    def post_empty_trade_commander(self):
        self.streamer_db["trade_commander"].insert_one({
            "time": self.trading_mode_now_time,
            "execute_trade": False,
            "is_time_flow_above_exhaust": self.is_time_flow_above_exhaust,
            "is_oppty": self.is_oppty,
            "is_royal_spread": self.is_royal_spread,
            "streamer_mctu": self.streamer_min_trading_coin,
            "mctu_spread_threshold": self.mctu_spread_threshold,
            "mctu_royal_spread": self.mctu_royal_spread,
            "settlement": False
        })

    """
    =======================
    || TRADING MODE ONLY ||
    =======================
    """

    def get_latest_orderbook(self):
        # get mm1, mm2 collection by target_currency
        mm1_col = getattr(SharedMongoClient, "get_%s_db" % self.mm1_name)()[self.target_currency + "_orderbook"]
        mm2_col = getattr(SharedMongoClient, "get_%s_db" % self.mm2_name)()[self.target_currency + "_orderbook"]

        # get latest db
        self.mm1_ob, self.mm2_ob = SharedMongoClient.get_latest_data_from_db(mm1_col, mm2_col)

    def get_min_tradable_coin_unit_spread_list_trading_mode(self):

        mm1_rq = Global.convert_epoch_to_local_datetime(self.mm1_ob["requestTime"], timezone="kr")
        mm2_rq = Global.convert_epoch_to_local_datetime(self.mm2_ob["requestTime"], timezone="kr")

        logging.warning("[REQUEST TIME] -- mm1: %s, mm2: %s\n" % (mm1_rq, mm2_rq))

        # analyze by MCTS
        target_spread_info \
            = MCTSAnalyzer.min_coin_tradable_spread_strategy(self.mm1_ob, self.mm2_ob,
                                                             self.mm1.taker_fee,
                                                             self.mm2.taker_fee,
                                                             self.streamer_min_trading_coin)[self.trade_type]

        logging.warning("========= [OPPTY NOTIFIER] ========")
        # if there is no Oppty,
        if target_spread_info.able_to_trade is False:
            self.is_oppty = False
            self.is_royal_spread = False
            logging.error("[WARNING] There is no oppty.. Waiting")
            logging.error("=> Fail reason: %s\n" % target_spread_info.fail_reason)
            return

        # if oppty,
        self.is_oppty = True
        logging.critical("[HOORAY] Oppty detected!!! now evaluating spread infos..")
        logging.critical("[SPREAD TO TRADE]: %.4f\n" % target_spread_info.spread_to_trade)

        # if gte royal spread,
        if target_spread_info.spread_to_trade >= self.mctu_royal_spread:
            self.is_royal_spread = True
            logging.critical("[!CONGRAT!] THIS WAS ROYAL SPREAD!! Now command to trade no matter what!! :D")
        else:
            self.is_royal_spread = False

        # get spread_to_trade list from min_trdble_coin_sprd_list
        self.present_spread_to_trade_list.extend([{"spread_to_trade": target_spread_info.spread_to_trade,
                                                   "sell_amt": target_spread_info.sell_order_amt,
                                                   "buy_amt": target_spread_info.buy_order_amt}])

    def trade_command_by_comparing_exhaustion_with_flow_time(self):

        # calc current time flowed rate
        time_flowed_rate = (self.trading_mode_now_time - self._bot_start_time) / self.TIME_DUR_OF_SETTLEMENT

        # calc current exhaust rate
        exhaust_rate = self.calc_latest_exhaust_rate()

        logging.warning("========== [EXHAUST INFO] =========")
        logging.warning("Time Flowed(%%): %.2f%% " % (time_flowed_rate * 100))
        logging.warning("Exhaustion(%%): %.2f%%\n" % (exhaust_rate * 100))

        if time_flowed_rate >= exhaust_rate:
            self.is_time_flow_above_exhaust = True
        else:
            self.is_time_flow_above_exhaust = False

    def calc_latest_exhaust_rate(self):

        # get mid price
        mm1_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(self.mm1_ob)
        mm2_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(self.mm2_ob)
        mid_price = (mm1_mid_price + mm2_mid_price) / 2

        # IF NEW
        if self.trade_type == "new":
            krw_to_exhaust = self.revenue_ledger["current_bal"]["krw"]["mm1"]
            coin_to_exhaust = self.revenue_ledger["current_bal"]["coin"]["mm2"] * mid_price

            # if krw bal is larger than coin converted to krw by real exchange rate,
            if krw_to_exhaust >= coin_to_exhaust:
                target_intial_balance = self.revenue_ledger["initial_bal"]["coin"]["mm2"]
                target_current_balance = self.revenue_ledger["current_bal"]["coin"]["mm2"]
            # if not,
            else:
                target_intial_balance = self.revenue_ledger["initial_bal"]["krw"]["mm1"]
                target_current_balance = self.revenue_ledger["current_bal"]["krw"]["mm1"]

        # IF REV
        else:
            krw_to_exhaust = self.revenue_ledger["current_bal"]["krw"]["mm2"]
            coin_to_exhaust = self.revenue_ledger["current_bal"]["coin"]["mm1"] * mid_price

            # if krw bal is larger than coin converted to krw by real exchange rate,
            if krw_to_exhaust >= coin_to_exhaust:
                target_intial_balance = self.revenue_ledger["initial_bal"]["coin"]["mm1"]
                target_current_balance = self.revenue_ledger["current_bal"]["coin"]["mm1"]
            # if not,
            else:
                target_intial_balance = self.revenue_ledger["initial_bal"]["krw"]["mm2"]
                target_current_balance = self.revenue_ledger["current_bal"]["krw"]["mm2"]

        return round(float(1 - (target_current_balance / target_intial_balance)), 5)

    def post_trade_commander_to_mongo(self):

        if self.is_time_flow_above_exhaust and self.is_oppty:
            execute_trade = True
        else:
            if self.is_royal_spread:
                execute_trade = True
            else:
                execute_trade = False

        self.streamer_db["trade_commander"].insert_one({
            "time": self.trading_mode_now_time,
            "execute_trade": execute_trade,
            "is_time_flow_above_exhaust": self.is_time_flow_above_exhaust,
            "is_oppty": self.is_oppty,
            "is_royal_spread": self.is_royal_spread,
            "streamer_mctu": self.streamer_min_trading_coin,
            "mctu_spread_threshold": self.mctu_spread_threshold,
            "mctu_royal_spread": self.mctu_royal_spread,
            "settlement": self.settlment_reached
        })

    def log_present_mctu_info(self, anal_start_time: int, anal_end_time: int):
        local_anal_st = Global.convert_epoch_to_local_datetime(anal_start_time, timezone="kr")
        local_anal_et = Global.convert_epoch_to_local_datetime(anal_end_time, timezone="kr")

        logging.warning("=========== [MCTU INFO] ==========")
        logging.warning("[Anal Duration]: %s - %s" % (local_anal_st, local_anal_et))
        logging.warning("\n[SPREAD RECORDER]:\n%s"
                        % self.get_mctu_spread_and_frequency(self.present_spread_to_trade_list))

    @staticmethod
    def trading_mode_loop_sleep_handler(mode_start_time: int, mode_end_time: int, mode_loop_interval: int):
        run_time = mode_end_time - mode_start_time
        time_to_wait = int(mode_loop_interval - run_time)
        if time_to_wait > 0:
            time.sleep(time_to_wait)

    def post_settlement_commander(self):
        self.streamer_db["trade_commander"].insert_one({
            "time": self.trading_mode_now_time,
            "trade": False,
            "settlement": True
        })

    """
    ======================
    || UNIVERSALLY USED ||
    ======================
    """

    def settlement_handler(self):
        message = "Settlement reached!! now closing Trade Streamer!!"
        logging.error(message)
        Global.send_to_slack_channel(Global.SLACK_STREAM_STATUS_URL, message)

        # command Acutal Trader to stop
        self.post_settlement_commander()

        # wait until Acutal Trader stops trading (in case actual balance unmatch)
        time.sleep(self.TRADING_MODE_LOOP_INTERVAL)

        # post settled balance info to MongoDB
        self.update_balance()
        self.update_revenue_ledger(mode_status="settlement")

        # post latest_rate_info
        self.post_backup_to_mongo_when_died(is_accident=False)

        # finally, halt sys
        sys.exit()

    @staticmethod
    def get_mctu_spread_and_frequency(spread_to_trade_list: list):
        result = str()

        if len(spread_to_trade_list) == 0:
            result = "* spread: Null -- frequency: Null\n"
            return result

        # extract spread only list from spread to trade list
        spread_list = [spread_info["spread_to_trade"] for spread_info in spread_to_trade_list]
        spread_list.sort(reverse=True)

        total_count = len(list(spread_list))
        for key, group in groupby(spread_list):
            cur_group_count = len(list(group))
            result += "* spread: %.2f -- frequency: %.2f%% -- count: %d out of %d\n" \
                      % (key, (cur_group_count / total_count) * 100, cur_group_count, total_count)
        return result

    def log_rev_ledger(self):
        logging.warning("========= [REV LEDGER INFO] ========")
        logging.warning("------------------------------------")
        target_data = self.revenue_ledger["initial_bal"]
        logging.warning("<<< Initial Balance >>>")
        logging.warning("[ mm1 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm1"],
                                                         self.target_currency, target_data["coin"]["mm1"]))
        logging.warning("[ mm2 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm2"],
                                                         self.target_currency, target_data["coin"]["mm2"]))
        logging.warning("[total] krw: %.5f, %s: %.5f" % (target_data["krw"]["total"],
                                                         self.target_currency, target_data["coin"]["total"]))
        logging.warning("------------------------------------")

        target_data = self.revenue_ledger["current_bal"]
        logging.warning("<<< Current Balance >>>")
        logging.warning("[ mm1 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm1"],
                                                         self.target_currency, target_data["coin"]["mm1"]))
        logging.warning("[ mm2 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm2"],
                                                         self.target_currency, target_data["coin"]["mm2"]))
        logging.warning("[total] krw: %.5f, %s: %.5f" % (target_data["krw"]["total"],
                                                         self.target_currency, target_data["coin"]["total"]))
        logging.warning("------------------------------------\n\n\n")

    def update_balance(self):

        # check from Mongo Balance Commander whether to update or not
        latest_bal_cmd = self.streamer_db["balance_commander"].find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )

        # if no command, return
        if not latest_bal_cmd["is_bal_update"]:
            return

        # else, update using API
        self.mm1.update_balance()
        self.mm2.update_balance()

        self.mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
        self.mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
        self.mm1_coin_bal = float(self.mm1.balance.get_available_coin(self.target_currency))
        self.mm2_coin_bal = float(self.mm2.balance.get_available_coin(self.target_currency))

    def get_otc_result_init_mode(self, rewined_time: int, anal_end_time: int):
        # OTC target combination
        iyo_config = Global.read_iyo_setting_config(self.target_currency)

        self.target_settings = TradeSettingConfig.get_settings(mm1_name=self.mm1_name,
                                                               mm2_name=self.mm2_name,
                                                               target_currency=self.target_currency,
                                                               start_time=rewined_time,
                                                               end_time=anal_end_time,
                                                               division=iyo_config["division"],
                                                               depth=iyo_config["depth"],
                                                               consecution_time=iyo_config["consecution_time"],
                                                               is_virtual_mm=True)
        self.target_settings["mm1"]["krw_balance"] = self.mm1_krw_bal
        self.target_settings["mm1"]["coin_balance"] = self.mm1_coin_bal
        self.target_settings["mm2"]["krw_balance"] = self.mm2_krw_bal
        self.target_settings["mm2"]["coin_balance"] = self.mm2_coin_bal

        return OpptyTimeCollector.run(settings=self.target_settings)

    def update_revenue_ledger(self, mode_status: str):

        # get recent bal to append
        bal_to_append = {
            "krw": {
                "mm1": self.mm1_krw_bal,
                "mm2": self.mm2_krw_bal,
                "total": self.mm1_krw_bal + self.mm2_krw_bal
            },
            "coin": {
                "mm1": self.mm1_coin_bal,
                "mm2": self.mm2_coin_bal,
                "total": self.mm1_coin_bal + self.mm2_coin_bal
            }
        }

        # if initiation mdoe, append bal to initial, current balance
        if self.is_initiation_mode:
            self.revenue_ledger = {
                "time": self.streamer_start_time,
                "mode_status": mode_status,
                "target_currency": self.target_currency,
                "mm1_name": self.mm1_name,
                "mm2_name": self.mm2_name,
                "initial_bal": bal_to_append,
                "current_bal": bal_to_append
            }

        # if trading mdoe, only append to current balance
        elif self.is_trading_mode:
            self.revenue_ledger["time"] = self.trading_mode_now_time
            self.revenue_ledger["mode_status"] = mode_status
            self.revenue_ledger["current_bal"] = bal_to_append

        else:
            raise Exception("Something went wrong while appending conducting Revenue Ledger!")

        # finally post to Mongo DB
        self.streamer_db["revenue_ledger"].insert_one(dict(self.revenue_ledger))

    def post_backup_to_mongo_when_died(self, is_accident: bool):
        if not is_accident:
            to_post = {
                "is_accident": is_accident
            }
        else:
            to_post = {
                "is_accident": is_accident,
                "time_died": int(time.time()),
                "trade_type": self.trade_type,
                "spread_threshold": self.mctu_spread_threshold,
                "royal_spread_threshold": self.mctu_royal_spread,
                "time_flow_rate": {
                    "bot_start_time": self._bot_start_time if not None else self.streamer_start_time,
                    "time_dur_of_settlement": self.TIME_DUR_OF_SETTLEMENT
                },
                "exhaust_rate": {
                    "initial_balance": {
                        "krw": self.revenue_ledger["initial_balance"]
                    }
                }
            }
        self.streamer_db["backup"].insert_one(to_post)
