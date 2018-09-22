import logging
import time
from itertools import groupby

import pymongo

from analyzer.trade_analyzer import MCTSAnalyzer
from collector.oppty_time_collector import OpptyTimeCollector
from collector.rev_ledger_to_xlsx import RevLedgerXLSX
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from config.trade_setting_config import TradeSettingConfig
from trader.market_manager.market_manager import MarketManager
from trader.trade_streamer.handler_ref import *


class TradeHandlerV2:
    MIN_TRDBLE_COIN_MLTPLIER = None
    TIME_DUR_OF_SETTLEMENT = None
    TRADING_MODE_LOOP_INTERVAL = 3

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager, is_test: bool):

        # steamer init relevant
        if is_test:
            self.streamer_db = SharedMongoClient.get_test_streamer_db()
        if not is_test:
            self.streamer_db = SharedMongoClient.get_streamer_db()

        # make instance of handler ref
        self.th_instance = Threshold()
        self.cond_instance = Condition()
        self.rec_instance = Recorder()

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

        # MCTU relevant
        self.mm1_ob = None
        self.mm2_ob = None
        self.streamer_min_trading_coin = None

        # TIME relevant
        self.streamer_start_time = int(time.time())
        self.ocat_rewind_time = None
        self._bot_start_time = None
        self._settlement_time = None
        self.trading_mode_now_time = None

    """
    ==========================
    || INITIATION MODE ONLY ||
    ==========================
    """

    def set_initial_trade_setting(self):
        # set streamer_min_trading_coin
        self.MIN_TRDBLE_COIN_MLTPLIER = float(input("Please indicate Min Tradable Coin Multiplier (gte 1.0) "))
        self.streamer_min_trading_coin \
            = max(Global.read_min_trading_coin(self.mm1_name, self.target_currency),
                  Global.read_min_trading_coin(self.mm2_name, self.target_currency)) * self.MIN_TRDBLE_COIN_MLTPLIER

        # set settlement related var
        settle_hour = int(input("Please indicate settlement hour (int only)"))
        settle_min = int(input("Please indicate settlement minute (int only)"))
        anal_rewind_hr = int(input("Please indicate [Initiation Mode] Rewind hour (int only)"))
        self.TIME_DUR_OF_SETTLEMENT = settle_hour * 60 * 60 + settle_min * 60

        # set rewind time for MCTU anal init mode
        self.ocat_rewind_time = int(self.streamer_start_time - anal_rewind_hr * 60 * 60)

    def get_past_mctu_spread_info_init_mode(self, anal_start_time: int, anal_end_time: int):
        """mtcu: Min Tradable Coin Unit
        """

        # get OTC from determined combination
        otc_result_dict = self.get_otc_result_init_mode(anal_start_time, anal_end_time)

        # get mm1, mm2 collection by target_currency
        mm1_col = getattr(SharedMongoClient, "get_%s_db" % self.mm1_name)()[self.target_currency + "_orderbook"]
        mm2_col = getattr(SharedMongoClient, "get_%s_db" % self.mm2_name)()[self.target_currency + "_orderbook"]

        # loop through sliced_oppty_dur and launch backtesting
        for trade_type in ["new", "rev"]:
            for sliced_time_list in otc_result_dict[trade_type]:
                start_time = sliced_time_list[0]
                end_time = sliced_time_list[1]

                mm1_cursor, mm2_cursor = SharedMongoClient.get_data_from_db(mm1_col, mm2_col, start_time, end_time)

                for mm1_data, mm2_data in zip(mm1_cursor, mm2_cursor):
                    spread_info_dict = MCTSAnalyzer.min_coin_tradable_spread_strategy(
                        mm1_data, mm2_data, self.mm1.taker_fee, self.mm2.taker_fee, self.streamer_min_trading_coin)
                    target_spread_info = spread_info_dict[trade_type]
                    if (target_spread_info.able_to_trade is False) or (target_spread_info.spread_to_trade < 0):
                        continue

                    self.rec_instance.spread_dict["init"][trade_type].append({
                        "spread_to_trade": target_spread_info.spread_to_trade,
                        "sell_amt": target_spread_info.sell_order_amt,
                        "buy_amt": target_spread_info.buy_order_amt})
        return

    def set_time_relevant_before_trading_mode(self):
        self.trading_mode_now_time = int(time.time())
        self._bot_start_time = self.trading_mode_now_time
        self._settlement_time = self._bot_start_time + self.TIME_DUR_OF_SETTLEMENT

    def get_otc_result_init_mode(self, rewined_time: int, anal_end_time: int):
        # OTC target combination
        iyo_config = Global.read_iyo_setting_config(self.target_currency)

        target_settings = TradeSettingConfig.get_settings(mm1_name=self.mm1_name,
                                                          mm2_name=self.mm2_name,
                                                          target_currency=self.target_currency,
                                                          start_time=rewined_time,
                                                          end_time=anal_end_time,
                                                          division=iyo_config["division"],
                                                          depth=iyo_config["depth"],
                                                          consecution_time=iyo_config["consecution_time"],
                                                          is_virtual_mm=True)
        target_settings["mm1"]["krw_balance"] = self.mm1_krw_bal
        target_settings["mm1"]["coin_balance"] = self.mm1_coin_bal
        target_settings["mm2"]["krw_balance"] = self.mm2_krw_bal
        target_settings["mm2"]["coin_balance"] = self.mm2_coin_bal

        return OpptyTimeCollector.run(settings=target_settings)

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

    def update_trade_condition_by_mctu_analyzer(self):
        """mtcu: Min Tradable Coin Unit
        """

        mm1_rq = Global.convert_epoch_to_local_datetime(self.mm1_ob["requestTime"], timezone="kr")
        mm2_rq = Global.convert_epoch_to_local_datetime(self.mm2_ob["requestTime"], timezone="kr")

        logging.warning("[REQUEST TIME] -- mm1: %s, mm2: %s\n" % (mm1_rq, mm2_rq))

        # analyze by MCTS
        spread_info_dict = MCTSAnalyzer.min_coin_tradable_spread_strategy(self.mm1_ob, self.mm2_ob,
                                                                          self.mm1.taker_fee,
                                                                          self.mm2.taker_fee,
                                                                          self.streamer_min_trading_coin)

        new_cond = spread_info_dict["new"].able_to_trade
        rev_cond = spread_info_dict["rev"].able_to_trade

        logging.warning("========= [OPPTY NOTIFIER] ========")
        # if there is no Oppty,
        if new_cond is False and rev_cond is False:
            self.cond_instance.NEW["is_oppty"] = False
            self.cond_instance.NEW["is_royal"] = False
            self.cond_instance.REV["is_oppty"] = False
            self.cond_instance.REV["is_royal"] = False

            logging.error("[WARNING] There is no oppty.. Waiting")
            logging.error("=> [NEW] Fail reason: %s" % spread_info_dict["new"].fail_reason)
            logging.error("=> [REV] Fail reason: %s\n" % spread_info_dict["rev"].fail_reason)
            return

        # if oppty (NEW or REV)
        for trade_type in spread_info_dict.keys():
            if not spread_info_dict[trade_type].able_to_trade:
                getattr(self.cond_instance, trade_type.upper())["is_oppty"] = False
                getattr(self.cond_instance, trade_type.upper())["is_royal"] = False
                continue

            logging.critical("[HOORAY] [%s] Oppty detected!!! now evaluating spread infos.." % trade_type.upper())
            logging.critical("[SPREAD TO TRADE]: %.4f\n" % spread_info_dict[trade_type].spread_to_trade)

            getattr(self.cond_instance, trade_type.upper())["is_oppty"] = True

            # if gte royal spread,
            if spread_info_dict[trade_type].spread_to_trade >= getattr(self.th_instance, trade_type.upper())["royal"]:
                getattr(self.cond_instance, trade_type.upper())["is_royal"] = True
                logging.critical("[!CONGRAT!] THIS WAS ROYAL SPREAD!! Now command to trade no matter what!! :D")
            else:
                getattr(self.cond_instance, trade_type.upper())["is_royal"] = False

            # get spread_to_trade list from min_trdble_coin_sprd_list
            self.rec_instance.spread_dict["trade"][trade_type].extend(
                [{"spread_to_trade": spread_info_dict[trade_type].spread_to_trade,
                  "sell_amt": spread_info_dict[trade_type].sell_order_amt,
                  "buy_amt": spread_info_dict[trade_type].buy_order_amt}])

    def renew_exhaust_condition_by_time_flow(self):

        # calc current time flowed rate
        time_flowed_rate = (self.trading_mode_now_time - self._bot_start_time) / self.TIME_DUR_OF_SETTLEMENT

        # calc current exhaust rate
        exhaust_rate_dict = Exhaustion.rate_to_dict(self.mm1_ob, self.mm2_ob, self.rec_instance.rev_ledger)

        for trade_type in exhaust_rate_dict.keys():
            logging.warning("========== [ '%s' EXHAUST INFO] =========" % trade_type.upper())
            logging.warning("Time Flowed(%%): %.2f%% " % (time_flowed_rate * 100))
            logging.warning("Exhaustion(%%): %.2f%%\n" % (exhaust_rate_dict[trade_type] * 100))

            # adjust condition accordingly
            if time_flowed_rate >= exhaust_rate_dict[trade_type]:
                getattr(self.cond_instance, trade_type.upper())["is_time_flow_above_exhaust"] = True
            else:
                getattr(self.cond_instance, trade_type.upper())["is_time_flow_above_exhaust"] = False

    @staticmethod
    def trading_mode_loop_sleep_handler(mode_start_time: int, mode_end_time: int, mode_loop_interval: int):
        run_time = mode_end_time - mode_start_time
        time_to_wait = int(mode_loop_interval - run_time)
        if time_to_wait > 0:
            time.sleep(time_to_wait)

    """
    ============================
    || Mongo Post % Universal ||
    ============================
    """

    def post_empty_trade_commander(self):
        self.streamer_db["trade_commander"].insert_one(
            TradeCommander.to_dict(
                time=self.streamer_start_time,
                streamer_mctu=self.streamer_min_trading_coin,
                condition=self.cond_instance,
                threshold=self.th_instance
            )
        )

    def post_empty_bal_commander(self):
        self.streamer_db["balance_commander"].insert_one(dict(is_bal_update=False))

    def post_trade_commander_to_mongo(self):

        self.streamer_db["trade_commander"].insert_one(
            TradeCommander.to_dict(
                time=self.trading_mode_now_time,
                streamer_mctu=self.streamer_min_trading_coin,
                condition=self.cond_instance,
                threshold=self.th_instance
            )
        )

    def post_settlement_commander(self):
        self.streamer_db["trade_commander"].insert_one(TradeCommander.to_dict(
            time=self.trading_mode_now_time,
            streamer_mctu=self.streamer_min_trading_coin,
            condition=self.cond_instance,
            threshold=self.th_instance
        ))

    def settlement_handler(self):
        message = "Settlement reached!! now closing Trade Streamer!!"
        logging.warning(message)
        Global.send_to_slack_channel(Global.SLACK_STREAM_STATUS_URL, message)

        # set settle cond True
        self.cond_instance.is_settlement = True

        # command Acutal Trader to stop
        self.post_settlement_commander()

        # wait until Acutal Trader stops trading (in case actual balance unmatch)
        time.sleep(self.TRADING_MODE_LOOP_INTERVAL)

        # post settled balance info to MongoDB
        self.update_balance(mode_status="settlement")
        self.update_revenue_ledger(mode_status="settlement")

        # write RevLedgerXLXS
        self.launch_rev_ledger_xlsx(mode_status="settlement")

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

    def update_balance(self, mode_status: str):

        # check from Mongo Balance Commander whether to update or not
        latest_bal_cmd = self.streamer_db["balance_commander"].find_one(
            sort=[('_id', pymongo.DESCENDING)]
        )

        # if trading mode,
        if mode_status == "trading":
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
        if mode_status == "initiation":
            self.rec_instance.rev_ledger = {
                "time": self.streamer_start_time,
                "mode_status": mode_status,
                "target_currency": self.target_currency,
                "mm1_name": self.mm1_name,
                "mm2_name": self.mm2_name,
                "initial_bal": bal_to_append,
                "current_bal": bal_to_append
            }

        # if trading mdoe, only append to current balance
        elif mode_status == "trading" or mode_status == "settlement":
            self.rec_instance.rev_ledger["time"] = self.trading_mode_now_time
            self.rec_instance.rev_ledger["mode_status"] = mode_status
            self.rec_instance.rev_ledger["current_bal"] = bal_to_append

        else:
            raise Exception("Mode status injected is invalid for Revenue Ledger!")

        # finally post to Mongo DB
        self.streamer_db["revenue_ledger"].insert_one(dict(self.rec_instance.rev_ledger))

    def launch_rev_ledger_xlsx(self, mode_status: str):
        RevLedgerXLSX(self.target_currency, self.mm1_name, self.mm2_name).run(mode_status=mode_status)

    """
    ============
    || Logger ||
    ============
    """

    def log_init_mode_mctu_info(self):
        local_anal_st = Global.convert_epoch_to_local_datetime(self.ocat_rewind_time, timezone="kr")
        local_anal_et = Global.convert_epoch_to_local_datetime(self.streamer_start_time, timezone="kr")

        logging.warning("=========== [MCTU INFO] ==========")
        logging.warning("[Anal Duration]: %s - %s" % (local_anal_st, local_anal_et))

        target_dict = self.rec_instance.spread_dict["init"]
        for trade_type in target_dict.keys():
            logging.warning("['%s' SPREAD RECORDER]:\n%s"
                            % (trade_type.upper(),
                               self.get_mctu_spread_and_frequency(target_dict[trade_type])))

        self.th_instance.NEW["normal"] = float(input("Decide [NEW] MCTU spread threshold: "))
        self.th_instance.NEW["royal"] = float(input("Decide [NEW] MCTU Royal spread: "))
        self.th_instance.REV["normal"] = float(input("Decide [REV] MCTU spread threshold: "))
        self.th_instance.REV["royal"] = float(input("Decide [REV] MCTU Royal spread: "))

    def log_trading_mode_mctu_info(self, anal_start_time: int, anal_end_time: int):
        local_anal_st = Global.convert_epoch_to_local_datetime(anal_start_time, timezone="kr")
        local_anal_et = Global.convert_epoch_to_local_datetime(anal_end_time, timezone="kr")

        logging.warning("=========== [MCTU INFO] ==========")
        logging.warning("[Anal Duration]: %s - %s" % (local_anal_st, local_anal_et))

        target_dict = self.rec_instance.spread_dict["trade"]
        for trade_type in target_dict.keys():
            logging.warning("\n\n[ '%s' SPREAD RECORDER]:\n%s"
                            % (trade_type.upper(),
                               self.get_mctu_spread_and_frequency(target_dict[trade_type])))

    def log_rev_ledger(self):
        logging.warning("========= [REVENUE LEDGER INFO] ========")
        logging.warning("------------------------------------")
        target_data = self.rec_instance.rev_ledger["initial_bal"]
        logging.warning("<<< Initial Balance >>>")
        logging.warning("[ mm1 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm1"],
                                                         self.target_currency, target_data["coin"]["mm1"]))
        logging.warning("[ mm2 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm2"],
                                                         self.target_currency, target_data["coin"]["mm2"]))
        logging.warning("[total] krw: %.5f, %s: %.5f" % (target_data["krw"]["total"],
                                                         self.target_currency, target_data["coin"]["total"]))
        logging.warning("------------------------------------")

        target_data = self.rec_instance.rev_ledger["current_bal"]
        logging.warning("<<< Current Balance >>>")
        logging.warning("[ mm1 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm1"],
                                                         self.target_currency, target_data["coin"]["mm1"]))
        logging.warning("[ mm2 ] krw: %.5f, %s: %.5f" % (target_data["krw"]["mm2"],
                                                         self.target_currency, target_data["coin"]["mm2"]))
        logging.warning("[total] krw: %.5f, %s: %.5f" % (target_data["krw"]["total"],
                                                         self.target_currency, target_data["coin"]["total"]))
        logging.warning("------------------------------------\n\n\n")
