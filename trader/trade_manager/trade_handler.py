import time
import logging
import pymongo
from pymongo.collection import Collection
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from analyzer.trade_analyzer import BasicAnalyzer
from config.config_market_manager import ConfigMarketManager
from optimizer.base_optimizer import BaseOptimizer
from config.trade_setting_config import TradeSettingConfig
from collector.scheduler.otc_scheduler import OTCScheduler
from collector.oppty_time_collector import OpptyTimeCollector
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer
from trader.market_manager.market_manager import MarketManager
from trader.trade_manager.trade_stat_formula import TradeFormulaApplied


class TradeHandler:
    TIME_DUR_OF_SETTLEMENT = 3 * 60 * 60
    INITIATION_REWEIND_TIME = 30 * 60

    TRADING_MODE_LOOP_INTERVAL = 2

    MAX_TRADING_COIN_DIVISION = 10

    EXHAUST_CTRL_DIVISION = 10

    YIELD_THRESHOLD_RATE_START = 0.1
    YIELD_THRESHOLD_RATE_END = 0.5
    YIELD_THRESHOLD_RATE_STEP = 0.05

    FTI_FORMULA_WEIGHT_START = 0.1
    FTI_FORMULA_WEIGHT_END = 1.0
    FTI_FORMULA_WEIGHT_STEP = 0.05

    FTI_MIN_INTERVAL = 5

    MAX_TI_MULTIPLIER_START = 1
    MAX_TI_MULTIPLIER_END = 5
    MAX_TI_MULTIPLIER_STEP = 1

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager,
                 is_initiation_mode: bool, is_trading_mode: bool):

        self.streamer_db = SharedMongoClient.get_streamer_db()

        self.is_initiation_mode = is_initiation_mode
        self.is_trading_mode = is_trading_mode

        self.ocat_final_result = None

        self.mm1 = mm1
        self.mm2 = mm2
        self.mm1_name = self.mm1.get_market_name().lower()
        self.mm2_name = self.mm2.get_market_name().lower()
        self.mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
        self.mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
        self.mm1_coin_bal = float(self.mm1.balance.get_available_coin(target_currency))
        self.mm2_coin_bal = float(self.mm2.balance.get_available_coin(target_currency))
        self.target_currency = target_currency

        self.slicing_interval = Global.read_sliced_iyo_setting_config(self.target_currency)["slicing_interval"]

        self.bot_start_time = int(time.time())
        self.rewined_time = int(self.bot_start_time - self.INITIATION_REWEIND_TIME)

        self.initiation_start_time = int(time.time())
        self.init_rewined_time = int(self.initiation_start_time - self.INITIATION_REWEIND_TIME)

        self.trading_mode_start_time = None
        self.trading_mode_rewined_time = None

        self.bot_start_time = None
        self.settlement_time = None

        self.exhaust_booster = 2
        self.exhaust_inhibitor = 0.5
        self.cur_exhaust_ctrl_stage = 0
        self.init_exhaust_ctrl_currency_bal = None
        self.cur_exhaust_ctrl_currency_bal = None

    """
    ==========================
    || INITIATION MODE ONLY ||
    ==========================
    """

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

            # save this setting for updating IYO setting in future ref
            self.ocat_final_result = ocat_final_result

        else:
            raise Exception("Please indicate if it is Inner OCAT or not")

        descending_order_result = OTCScheduler.sort_by_logest_oppty_time_to_lowest(ocat_final_result)
        top_ten_descend_order_result = descending_order_result[:10]

        for result in top_ten_descend_order_result:
            new_percent = (result["new"] / self.INITIATION_REWEIND_TIME) * 100
            rev_percent = (result["rev"] / self.INITIATION_REWEIND_TIME) * 100
            new_spread_strength = result["new_spread_ratio"] * 100
            rev_spread_strength = result["rev_spread_ratio"] * 100

            logging.warning("[%s] NEW: %.2f%%, REV: %.2f%% // NEW_SPREAD_STRENGTH: %.2f%%, REV_SPREAD_STRENGTH: %.2f%%"
                            % (result["combination"], new_percent, rev_percent,
                               new_spread_strength, rev_spread_strength))

    def to_proceed_handler_for_initiation_mode(self):

        to_proceed = str(input("Inner & Outer OCAT finished. Do you want to change any settings? (y/n)"))
        if to_proceed == "y":
            # set settings accordingly
            self.target_currency = str(input("Type target_currency:"))
            self.mm1: MarketManager = getattr(ConfigMarketManager, input("Type MM1!! ex) bithumb :").upper()).value
            self.mm2: MarketManager = getattr(ConfigMarketManager, input("Type MM2!! ex) BITHUMB :").upper()).value
            self.mm1_name = self.mm1.get_market_name().lower()
            self.mm2_name = self.mm2.get_market_name().lower()

            # update balance
            self.update_balance()

            logging.error("========== [INITIAL BALANCE] ================")
            logging.error("[%s Balance] >> KRW: %f, %s: %f" % (self.mm1_name.upper(), self.mm1_krw_bal,
                                                               self.target_currency.upper(),
                                                               self.mm1_coin_bal))
            logging.warning("[%s Balance] >> KRW: %f, %s: %f\n" % (self.mm2_name.upper(), self.mm2_krw_bal,
                                                                   self.target_currency.upper(),
                                                                   self.mm2_coin_bal))

            # change IYO config settings of krw, coin seq end
            self.update_bal_seq_end_by_recent_bal_init_mode()
            logging.error("Now initiating with changed settings!!")
            return True

        if to_proceed == "n":

            # update balance
            self.update_balance()

            logging.error("========== [INITIAL BALANCE] ================")
            logging.error("[%s Balance] >> KRW: %f, %s: %f" % (self.mm1_name.upper(), self.mm1_krw_bal,
                                                               self.target_currency.upper(),
                                                               self.mm1_coin_bal))
            logging.warning("[%s Balance] >> KRW: %f, %s: %f\n" % (self.mm2_name.upper(), self.mm2_krw_bal,
                                                                   self.target_currency.upper(),
                                                                   self.mm2_coin_bal))

            # change IYO config settings of krw, coin seq end
            self.update_bal_seq_end_by_recent_bal_init_mode()
            logging.error("Now initiating with current settings!!")
            return True

        else:
            logging.error("Irrelevant command. Please try again")
            return self.to_proceed_handler_for_initiation_mode()

    def otc_all_combination_by_one_coin(self, target_currency: str, combination_list: list):
        all_ocat_result_by_one_coin = []
        for _combi in combination_list:
            # draw iyo_config for settings
            iyo_config = Global.read_iyo_setting_config(target_currency)

            settings = TradeSettingConfig.get_settings(mm1_name=_combi[0],
                                                       mm2_name=_combi[1],
                                                       target_currency=target_currency,
                                                       start_time=self.init_rewined_time,
                                                       end_time=self.initiation_start_time,
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
                total_dur_dict["avg_new_mid_price"] = otc_result_dict["avg_new_mid_price"]
                total_dur_dict["avg_rev_mid_price"] = otc_result_dict["avg_rev_mid_price"]
                total_dur_dict["combination"] = \
                    "%s-%s-%s" % (target_currency.upper(), str(_combi[0]).upper(), str(_combi[1]).upper())

                all_ocat_result_by_one_coin.append(total_dur_dict)
            except TypeError as e:
                logging.error("Something went wrong in OTC scheduler", e)
                continue

        return all_ocat_result_by_one_coin

    def update_bal_seq_end_by_recent_bal_init_mode(self):

        rough_exhaust_divider = self.INITIATION_REWEIND_TIME / self.TIME_DUR_OF_SETTLEMENT * self.EXHAUST_CTRL_DIVISION
        Global.write_balance_seq_end_to_ini(
            krw_seq_end=(self.mm1_krw_bal + self.mm2_krw_bal / rough_exhaust_divider),
            coin_seq_end=(self.mm1_coin_bal + self.mm2_coin_bal) / rough_exhaust_divider)

        # todo: 나중에 코인가격 변하는거 고려해서 주기적으로 업뎃하는거 만들기
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

        max_trade_coin_end = round(
            float((self.mm1_coin_bal + self.mm2_coin_bal) / 2 / self.MAX_TRADING_COIN_DIVISION), 4)
        threshold_end = int(max(
            target_ocat["new_max_unit_spread"], target_ocat["rev_max_unit_spread"]) * max_trade_coin_end)
        appx_unit_coin_price = int(max(target_ocat["avg_new_mid_price"], target_ocat["avg_rev_mid_price"]))

        Global.write_iyo_config_by_target_currency(self.target_currency,
                                                   max_trade_coin_end=max_trade_coin_end,
                                                   threshold_end=threshold_end,
                                                   appx_unit_coin_price=appx_unit_coin_price)

    def reset_time_relevant_before_trading_mode(self):
        self.trading_mode_rewined_time = self.initiation_start_time
        self.trading_mode_start_time = int(time.time())
        self.bot_start_time = int(time.time())
        self.settlement_time = self.bot_start_time + self.TIME_DUR_OF_SETTLEMENT

    """
    =======================
    || TRADING MODE ONLY ||
    =======================
    """

    def update_bal_seq_end_by_recent_bal_and_exhaust_ctrl(self):

        # update exhaust_ctrl_currency
        self.update_exhaust_ctrl_target_currency()

        # update exhaust_ctrl_stage
        self.update_exhaust_stage()

        # evaluate current exhaust rate and decide whether to boost or inhibit
        current_exhaust_rate = 1 - (self.cur_exhaust_ctrl_currency_bal / self.init_exhaust_ctrl_currency_bal)

        if current_exhaust_rate <= self.cur_exhaust_ctrl_stage / self.EXHAUST_CTRL_DIVISION:
            exhaust_rate_divider = self.EXHAUST_CTRL_DIVISION / self.exhaust_booster
        else:
            exhaust_rate_divider = self.EXHAUST_CTRL_DIVISION / self.exhaust_inhibitor

        # finally, create seq with initial bal and evaluated divider
        latest_rev_ledger = self.streamer_db["revenue_ledger"].find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )
        initial_total_krw = latest_rev_ledger["initial_bal"]["krw"]["total"]
        initial_total_coin = latest_rev_ledger["initial_bal"]["coin"]["total"]

        krw_seq_end = initial_total_krw / exhaust_rate_divider
        coin_seq_end = initial_total_coin / exhaust_rate_divider

        Global.write_balance_seq_end_to_ini(krw_seq_end=krw_seq_end,
                                            coin_seq_end=coin_seq_end)

        # log its result in order to analyze deeper
        logging.warning("\n========= [EXHAUSTION INFO Report] =========")
        logging.warning("Current Exhst rate: %.4f" % current_exhaust_rate)
        logging.warning("Current Exhst Ctrl Stage: %d" % self.cur_exhaust_ctrl_stage)
        logging.warning("[KRW] seq end: %.5f" % krw_seq_end)
        logging.warning("[%s] seq end: %.5f\n" % (self.target_currency.upper(), coin_seq_end))

    def update_exhaust_stage(self):

        stage_length = int((self.settlement_time - self.bot_start_time) / self.EXHAUST_CTRL_DIVISION)
        if self.cur_exhaust_ctrl_stage is None:
            self.cur_exhaust_ctrl_stage = 1
        else:
            if int(time.time()) >= self.cur_exhaust_ctrl_stage * stage_length + self.bot_start_time:
                self.cur_exhaust_ctrl_stage += 1

    def update_exhaust_ctrl_target_currency(self):
        # retrieve latest s_iyo from MongoDB and decide b/t NEW and REV
        latest_s_iyo = self.streamer_db["s_iyo"].find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )

        latest_rev_ledger = self.streamer_db["revenue_ledger"].find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )

        mm1_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(
            self.mm1.get_orderbook(self.mm1.get_market_currency(self.target_currency)))
        mm2_mid_price, _, _ = BasicAnalyzer.get_orderbook_mid_price(
            self.mm2.get_orderbook(self.mm2.get_market_currency(self.target_currency)))

        mid_price = (mm1_mid_price + mm2_mid_price) / 2

        # IF NEW
        if latest_s_iyo["new_oppty_count"] >= latest_s_iyo["rev_oppty_count"]:
            krw_to_exhaust = latest_rev_ledger["current_bal"]["krw"]["mm1"]
            coin_to_exhaust = latest_rev_ledger["current_bal"]["coin"]["mm2"] * mid_price

            # if krw bal is larger than coin converted to krw by real exchange rate,
            if krw_to_exhaust >= coin_to_exhaust:
                self.init_exhaust_ctrl_currency_bal = latest_rev_ledger["initial_bal"]["coin"]["mm2"]
                self.cur_exhaust_ctrl_currency_bal = latest_rev_ledger["current_bal"]["coin"]["mm2"]
            # if not,
            else:
                self.init_exhaust_ctrl_currency_bal = latest_rev_ledger["initial_bal"]["krw"]["mm1"]
                self.cur_exhaust_ctrl_currency_bal = latest_rev_ledger["current_bal"]["krw"]["mm1"]

        # IF REV
        else:
            krw_to_exhaust = latest_rev_ledger["current_bal"]["krw"]["mm2"]
            coin_to_exhaust = latest_rev_ledger["current_bal"]["coin"]["mm1"] * mid_price

            # if krw bal is larger than coin converted to krw by real exchange rate,
            if krw_to_exhaust >= coin_to_exhaust:
                self.init_exhaust_ctrl_currency_bal = latest_rev_ledger["initial_bal"]["coin"]["mm1"]
                self.cur_exhaust_ctrl_currency_bal = latest_rev_ledger["current_bal"]["coin"]["mm1"]
            # if not,
            else:
                self.init_exhaust_ctrl_currency_bal = latest_rev_ledger["initial_bal"]["krw"]["mm2"]
                self.cur_exhaust_ctrl_currency_bal = latest_rev_ledger["current_bal"]["krw"]["mm2"]

    @staticmethod
    def trading_mode_loop_sleep_handler(mode_start_time: int, mode_end_time: int, mode_loop_interval: int):
        run_time = mode_end_time - mode_start_time
        time_to_wait = int(mode_loop_interval - run_time)
        if time_to_wait > 0:
            time.sleep(time_to_wait)

    def no_oppty_handler_for_trading_mode(self):
        # post empty fti_setting --> to make RFAB not to trade
        self.post_empty_fti_setting_to_mongo_when_no_oppty()
        self.trading_mode_loop_sleep_handler(self.trading_mode_start_time, int(time.time()),
                                             self.TRADING_MODE_LOOP_INTERVAL)
        # reset time relevant
        self.reset_time_relevant_for_trading_mode()

    def post_empty_fti_setting_to_mongo_when_no_oppty(self):
        self.streamer_db["fti_setting"].insert({
            "no_oppty": "True",
            "settlement": "False",
            "fti_iyo_list": []
        })

    def reset_time_relevant_for_trading_mode(self):
        self.trading_mode_start_time = int(time.time())
        self.trading_mode_rewined_time = self.trading_mode_start_time - self.slicing_interval

    def trade_handler_when_settlement_reached(self):
        logging.critical("Bot reached settlement time!! closing trade...")
        self.streamer_db["fti_setting"].insert({
            "no_oppty": "False",
            "settlement": "True",
            "fti_iyo_list": []
        })
        Global.send_to_slack_channel(Global.SLACK_STREAM_STATUS_URL,
                                     "Settlement reached for [%s-%s-%s] RFAB! Closing Trade Streamer.."
                                     % (self.target_currency.upper(), self.mm1_name.upper(), self.mm2_name.upper()))

    """
    ===========================================
    || INITIATION & TRADING MODE (UNIVERSAL) ||
    ===========================================
    """

    @staticmethod
    def log_final_opt_result(final_opt_iyo_dict: dict):
        # log final_opt_iyo_dict
        logging.warning("\n======= [Trade Prediction Report] =======")
        logging.warning("FTI_exhaust_rate: %.5f" % final_opt_iyo_dict["fti_exhaust_rate"])
        logging.warning("FTI_yield_sum: %.5f" % final_opt_iyo_dict["fti_yield_sum"])
        logging.warning("Predicted_yield_by_settle: %.5f" % final_opt_iyo_dict["predicted_yield_by_settle"])
        logging.warning("\n========= [FTI Analysis Report] =========")
        logging.warning("yield_threshold_rate: %.2f" % final_opt_iyo_dict["yield_threshold_rate"])
        logging.warning("fti_formula_weight: %.2f" % final_opt_iyo_dict["fti_formula_weight"])
        logging.warning("max_time_interval_multiplier: %.2f\n" % final_opt_iyo_dict["max_time_interval_multiplier"])

    def update_balance(self):
        self.mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
        self.mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
        self.mm1_coin_bal = float(self.mm1.balance.get_available_coin(self.target_currency))
        self.mm2_coin_bal = float(self.mm2.balance.get_available_coin(self.target_currency))

    """
    ==========================
    || MONGO DB (UNIVERSAL) ||
    ==========================
    """

    def post_final_fti_result_to_mongodb(self, final_opt_iyo_dict):
        final_opt_iyo_dict["no_oppty"] = "False"
        final_opt_iyo_dict["settlement"] = "False"
        self.streamer_db["fti_setting"].insert(final_opt_iyo_dict)

    def post_updated_revenue_ledger(self):

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
            self.streamer_db["revenue_ledger"].insert({
                "target_currency": self.target_currency,
                "mm1_name": self.mm1_name,
                "mm2_name": self.mm2_name,
                "initial_bal": bal_to_append,
                "current_bal": bal_to_append
            })

        # if initiation mdoe, only append to current balance
        if self.is_trading_mode:
            latest_rev_ledger: Collection = self.streamer_db["revenue_ledger"].find_one(
                sort=[('_id', pymongo.DESCENDING)])
            latest_rev_ledger["current_bal"] = bal_to_append

    """
    ==============================
    || FTI ANALYSIS (UNIVERSAL) ||
    ==============================
    """

    def run_fti_analysis(self):

        # change time info up-to-date (since some minutes passed b/c of OCAT and Balance transfer
        if self.is_initiation_mode:
            logging.error("Now conducting [Initiation Mode >> FTI Analysis]")

            # launch Oppty Sliced IYO
            sliced_iyo_list = self.launch_oppty_sliced_iyo(self.initiation_start_time, self.init_rewined_time)

            # if no s_iyo data b/c of no oppty
            if len(sliced_iyo_list) == 0:
                logging.error("There was no oppty.. must have some oppty time when in Initiation Mode!!")
                return

            # post result to MongoDb
            self.streamer_db["s_iyo"].insert_many(sliced_iyo_list)

            # extract yield only dict data from s_iyo list
            extracted_yield_dict_list = TradeFormulaApplied.extract_yield_dict_from_s_iyo_list(sliced_iyo_list)

            bot_start_time = self.init_rewined_time

        elif self.is_trading_mode:
            logging.error("Now conducting [Trading Mode >> FTI Analysis]")

            # launch Oppty Sliced IYO
            small_s_iyo_list = self.launch_oppty_sliced_iyo(self.trading_mode_start_time,
                                                            self.trading_mode_rewined_time)

            # if no s_iyo data b/c of no oppty
            if len(small_s_iyo_list) == 0:
                logging.error(">>> There is no oppty time now...Waiting for oppty..")
                return

            # post this small dur s-iyo to MongoDB
            self.streamer_db["s_iyo"].insert_many(small_s_iyo_list)

            # get same amount of duration as of Initiation Mode from s_iyo DB
            s_iyo_col = self.streamer_db["s_iyo"]
            s_iyo_cur_list = s_iyo_col.find({"settings.start_time": {
                "$gte": self.bot_start_time,
                "$lte": self.trading_mode_start_time
            }}).sort([("start_time", 1)])

            sliced_iyo_list = []
            for iyo in s_iyo_cur_list:
                sliced_iyo_list.append(iyo)

            extracted_yield_dict_list = TradeFormulaApplied.extract_yield_dict_from_s_iyo_list(sliced_iyo_list)

            # analysis target is small_s_iyo_list (which is the most recent set), so change
            sliced_iyo_list = small_s_iyo_list

            bot_start_time = self.bot_start_time

        else:
            raise Exception("Trade Streamer should be launched with one of 2 modes -> "
                            "[INITIAL ANALYSIS MODE] or [TRADING MODE]")

        # get yield_histo_filtered dict
        yield_histo_filted_dict = TradeFormulaApplied.get_yield_histo_filtered_dict(extracted_yield_dict_list,
                                                                                    sliced_iyo_list,
                                                                                    self.YIELD_THRESHOLD_RATE_START,
                                                                                    self.YIELD_THRESHOLD_RATE_END,
                                                                                    self.YIELD_THRESHOLD_RATE_STEP)
        # launch Formulated Trade Interval (FTI)
        fti_result_list = self.launch_formulated_trade_interval(yield_histo_filted_dict, bot_start_time)

        # loop through all fti_result and get the best one expected yield and its infos
        final_opt_iyo_dict = self.get_opted_fti_one_result(fti_result_list)
        return final_opt_iyo_dict

    def launch_oppty_sliced_iyo(self, anal_start_time: int, rewinded_time: int):
        st_local = Global.convert_epoch_to_local_datetime(rewinded_time, timezone="kr")
        et_local = Global.convert_epoch_to_local_datetime(anal_start_time, timezone="kr")
        logging.critical("[%s-%s-%s] Sliced IYO conducting -> , start_time: %s, end_time: %s" % (
            self.target_currency.upper(), self.mm1_name.upper(), self.mm2_name.upper(), st_local, et_local))

        # draw iyo_config for bal & factor_setting
        sliced_iyo_config = Global.read_sliced_iyo_setting_config(self.target_currency)
        # set settings, bal_fact_settings, factor_settings
        settings = TradeSettingConfig.get_settings(mm1_name=self.mm1_name,
                                                   mm2_name=self.mm2_name,
                                                   target_currency=self.target_currency,
                                                   start_time=rewinded_time, end_time=anal_start_time,
                                                   division=sliced_iyo_config["division"],
                                                   depth=sliced_iyo_config["depth"],
                                                   consecution_time=sliced_iyo_config["consecution_time"],
                                                   is_virtual_mm=True)

        bal_factor_settings = TradeSettingConfig.get_bal_fact_settings(sliced_iyo_config["krw_seq_end"],
                                                                       sliced_iyo_config["coin_seq_end"])

        factor_settings = TradeSettingConfig.get_factor_settings(sliced_iyo_config["max_trade_coin_end"],
                                                                 sliced_iyo_config["threshold_end"],
                                                                 sliced_iyo_config["appx_unit_coin_price"])

        slicied_iyo_result = IntegratedYieldOptimizer.run(settings, bal_factor_settings, factor_settings,
                                                          is_stat_appender=False, is_slicing_dur=True,
                                                          slicing_interval=sliced_iyo_config["slicing_interval"])
        return slicied_iyo_result

    def launch_formulated_trade_interval(self, yield_histo_filted_dict: dict, bot_start_time: int):
        time_of_settlement = int(bot_start_time + self.TIME_DUR_OF_SETTLEMENT)

        fti_final_result_list = []
        for yield_th_rate in list(yield_histo_filted_dict.keys()):
            for fti_formul_weight in BaseOptimizer.generate_seq(self.FTI_FORMULA_WEIGHT_START,
                                                                self.FTI_FORMULA_WEIGHT_END,
                                                                self.FTI_FORMULA_WEIGHT_STEP):
                for max_ti_multi in BaseOptimizer.generate_seq(self.MAX_TI_MULTIPLIER_START, self.MAX_TI_MULTIPLIER_END,
                                                               self.MAX_TI_MULTIPLIER_STEP):
                    fti_iyos_result_dict = \
                        TradeFormulaApplied.get_formulated_trade_interval(list(yield_histo_filted_dict[yield_th_rate]),
                                                                          self.mm1_krw_bal, self.mm2_krw_bal,
                                                                          time_of_settlement,
                                                                          fti_formul_weight, self.FTI_MIN_INTERVAL,
                                                                          max_ti_multi)

                    # add these infos to yield_histo_filted_dict by its key value
                    fti_iyos_result_dict["yield_threshold_rate"] = yield_th_rate
                    fti_iyos_result_dict["fti_formula_weight"] = fti_formul_weight
                    fti_iyos_result_dict["max_time_interval_multiplier"] = max_ti_multi
                    fti_final_result_list.append(fti_iyos_result_dict)

        return fti_final_result_list

    """
    ==================================
    || FTI OPTIMIZER (FTI ANALYSIS) ||
    ==================================
    """

    def get_opted_fti_one_result(self, fti_result: list):
        # first, sort by the best fti yield
        yield_opted_fti_iyo_list = self.sort_fti_list_by_best_fti_yield(fti_result)

        # second, sort by min exhaust rate
        min_exhaust_rate_sorted_list = self.sort_yield_opted_fti_result_by_min_exhaust_rate(yield_opted_fti_iyo_list)

        # lastly, sort by min trade interval and return median result
        final_opted = self.sort_exhaust_rate_opt_fti_result_by_min_avg_trade_interval(min_exhaust_rate_sorted_list)

        return final_opted

    @staticmethod
    def sort_fti_list_by_best_fti_yield(fti_result: list):
        # retrieve final optimized setting by calculating fti_yield * fti_exhaust rate
        opted_yield = None
        yield_opted_fti_iyo_list = []
        for fti_iyo_dict in fti_result:
            predicted_yield_by_settle = fti_iyo_dict["predicted_yield_by_settle"]

            if opted_yield is None:
                opted_yield = predicted_yield_by_settle
                yield_opted_fti_iyo_list.append(fti_iyo_dict)
                continue
            if predicted_yield_by_settle > opted_yield:
                opted_yield = predicted_yield_by_settle
                yield_opted_fti_iyo_list.clear()
                yield_opted_fti_iyo_list.append(fti_iyo_dict)
            if predicted_yield_by_settle == opted_yield:
                yield_opted_fti_iyo_list.append(fti_iyo_dict)

        return yield_opted_fti_iyo_list

    @staticmethod
    def sort_yield_opted_fti_result_by_min_exhaust_rate(yield_opted_fti_iyo_list: list):
        if len(yield_opted_fti_iyo_list) > 1:
            min_exhaust_rate_sorted_list = []
            min_exhaust_rate = None

            for fti_result in yield_opted_fti_iyo_list:

                if min_exhaust_rate is None:
                    min_exhaust_rate = fti_result["fti_exhaust_rate"]
                    min_exhaust_rate_sorted_list.append(fti_result)
                    continue
                if min_exhaust_rate > fti_result["fti_exhaust_rate"]:
                    min_exhaust_rate = fti_result["fti_exhaust_rate"]
                    min_exhaust_rate_sorted_list.clear()
                    min_exhaust_rate_sorted_list.append(fti_result)
                if min_exhaust_rate == fti_result["fti_exhaust_rate"]:
                    min_exhaust_rate_sorted_list.append(fti_result)
                else:
                    continue
            return min_exhaust_rate_sorted_list
        else:
            return yield_opted_fti_iyo_list

    @staticmethod
    def sort_exhaust_rate_opt_fti_result_by_min_avg_trade_interval(final_opted_fti_iyo_list: list):
        # if len(final_opted_fti_iyo_list) =! 1, then choose the best one
        if len(final_opted_fti_iyo_list) > 1:

            min_ti_sorted_fti_iyo_list = []
            min_trade_interval = None
            for fti_iyo_dict in final_opted_fti_iyo_list:

                # calc avg trade_interval of current iyo_dict
                avg_trade_interval = 0
                for iyo in fti_iyo_dict["fti_iyo_list"]:
                    avg_trade_interval += iyo["fti"]

                # sort by minimum
                if min_trade_interval is None:
                    min_trade_interval = avg_trade_interval
                    min_ti_sorted_fti_iyo_list.append(fti_iyo_dict)
                    continue
                if min_trade_interval > avg_trade_interval:
                    min_trade_interval = avg_trade_interval
                    min_ti_sorted_fti_iyo_list.clear()
                    min_ti_sorted_fti_iyo_list.append(fti_iyo_dict)
                if min_trade_interval == avg_trade_interval:
                    min_ti_sorted_fti_iyo_list.append(fti_iyo_dict)
                else:
                    continue
            return Global.find_middle_of_list(min_ti_sorted_fti_iyo_list)
        else:
            return final_opted_fti_iyo_list[0]
