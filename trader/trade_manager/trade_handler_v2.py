import time
import logging
from analyzer.trade_analyzer import MCTSAnalyzer
from collector.oppty_time_collector import OpptyTimeCollector
from optimizer.integrated_yield_optimizer import IntegratedYieldOptimizer
from collector.scheduler.otc_scheduler import OTCScheduler
from config.config_market_manager import ConfigMarketManager
from config.global_conf import Global
from config.shared_mongo_client import SharedMongoClient
from config.trade_setting_config import TradeSettingConfig
from trader.market_manager.market_manager import MarketManager


class TradeHandlerV2:
    MIN_TRDBLE_COIN_MLTPLIER = 2

    TIME_DUR_OF_SETTLEMENT = 2 * 60 * 60

    TRADING_MODE_LOOP_INTERVAL = 5

    # this is useful when investing krw is big
    EXHAUST_CTRL_DIVISION = 20  # bigger it is, more frequently to apply exhaustion ctrl
    EXHAUST_CTRL_BOOSTER = 1.5  # if investing krw is small, recommand this lte 1
    EXHAUST_CTRL_INHIBITOR = 0.25  # if 1: no inhibit, less than 1 -> more inhibition

    YIELD_THRESHOLD_RATE = 0.2

    def __init__(self, target_currency: str, mm1: MarketManager, mm2: MarketManager):

        self.streamer_db = SharedMongoClient.get_streamer_db()

        self.is_initiation_mode = True
        self.is_trading_mode = False

        self.ocat_final_result = None

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

        self.trade_type = None
        self.streamer_min_trading_coin = None
        self.spread_to_trade_list = None
        self.init_krw_earned = 0

        self.slicing_interval = Global.read_sliced_iyo_setting_config(self.target_currency)["slicing_interval"]

        self.streamer_start_time = int(time.time())
        self.initiation_rewind_time = int(self.streamer_start_time - self.TIME_DUR_OF_SETTLEMENT)

        self._settlement_time = None

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
                                                       start_time=self.initiation_rewind_time,
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

        to_proceed = str(input("Inner & Outer OCAT finished. Do you want to change any settings? (Y/n)"))
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

        # update balance
        self.update_balance()

        # update streamer_min_trading_coin
        self.streamer_min_trading_coin \
            = max(Global.read_min_trading_coin(self.mm1_name, self.target_currency),
                  Global.read_min_trading_coin(self.mm2_name, self.target_currency)) * self.MIN_TRDBLE_COIN_MLTPLIER

        # set trade strategy
        self.trade_type = str(input("Insert Trade Strategy (new/rev): "))

        logging.warning("========== [INITIAL BALANCE] ================")
        logging.warning("[%s Balance] >> KRW: %f, %s: %f" % (self.mm1_name.upper(), self.mm1_krw_bal,
                                                             self.target_currency.upper(),
                                                             self.mm1_coin_bal))
        logging.warning("[%s Balance] >> KRW: %f, %s: %f\n" % (self.mm2_name.upper(), self.mm2_krw_bal,
                                                               self.target_currency.upper(),
                                                               self.mm2_coin_bal))
        logging.warning("Now initiating with typed settings!!")
        return True

    """
    =======================
    || TRADING MODE ONLY ||
    =======================
    """

    """
    ======================
    || UNIVERSALLY USED ||
    ======================
    """

    def get_min_tradable_coin_unit_spread_list(self, anal_start_time: int, anal_end_time: int):

        # get OTC from determined combination
        otc_result_dict = self.get_otc_result(anal_start_time, anal_end_time)

        # post to MongoDB to used in getting [min_trdable_unit_spread]
        self.streamer_db["otc_result"].insert(otc_result_dict)

        sliced_iyo_config = Global.read_sliced_iyo_setting_config(self.target_currency)

        # get sliced oppty dur dict by NEW or REV
        sliced_oppty_dur_list = IntegratedYieldOptimizer.get_sliced_oppty_dur_dict(
            otc_result_dict, sliced_iyo_config["slicing_interval"])

        # get mm1, mm2 collection by target_currency
        mm1_col = getattr(SharedMongoClient, "get_%s_db" % self.mm1_name)()[self.target_currency + "_orderbook"]
        mm2_col = getattr(SharedMongoClient, "get_%s_db" % self.mm2_name)()[self.target_currency + "_orderbook"]

        # loop through sliced_oppty_dur and launch backtesting
        min_trdble_coin_unit_sprd_list = []
        for sliced_time_list in sliced_oppty_dur_list:
            start_time = sliced_time_list[0]
            end_time = sliced_time_list[1]

            # fixme: 이 부분 커서에러 해결해야함
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

        # get spread_to_trade list from min_trdble_coin_sprd_list
        self.spread_to_trade_list = [spread_info.spread_to_trade for spread_info in min_trdble_coin_unit_sprd_list]

        # summate all spread_to_trade to get krw earning
        for spread_to_trade in self.spread_to_trade_list:
            self.init_krw_earned += spread_to_trade

    def update_balance(self):
        self.mm1_krw_bal = float(self.mm1.balance.get_available_coin("krw"))
        self.mm2_krw_bal = float(self.mm2.balance.get_available_coin("krw"))
        self.mm1_coin_bal = float(self.mm1.balance.get_available_coin(self.target_currency))
        self.mm2_coin_bal = float(self.mm2.balance.get_available_coin(self.target_currency))

    def get_otc_result(self, rewined_time: int, anal_end_time: int):
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
        return OpptyTimeCollector.run(settings=self.target_settings)
