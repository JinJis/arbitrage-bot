from trader.market.market import Market
from config.global_conf import Global


class TradeSettingConfig:

    @staticmethod
    def get_settings(mm1_name: str, mm2_name: str, target_currency: str, start_time: int, end_time: int, division: int,
                     depth: int, consecution_time: int, is_virtual_mm: bool):
        if is_virtual_mm:
            mm1_tag = "VIRTUAL_%s" % mm1_name.upper()
            mm2_tag = "VIRTUAL_%s" % mm2_name.upper()
        elif not is_virtual_mm:
            mm1_tag = mm1_name.upper()
            mm2_tag = mm2_name.upper()
        else:
            raise Exception("Please type mm1 and mm2 correctly! ex) coinone")

        return {
            "target_currency": target_currency,
            "mm1": {
                "market_tag": getattr(Market, mm1_tag),
                "taker_fee": Global.read_market_fee(mm1_name, is_taker_fee=True),
                "maker_fee": Global.read_market_fee(mm1_name, is_taker_fee=False),
                "min_trading_coin": Global.read_min_trading_coin(mm1_name, target_currency),
                "krw_balance": 1000000,
                "coin_balance": 10
            },
            "mm2": {
                "market_tag": getattr(Market, mm2_tag),
                "taker_fee": Global.read_market_fee(mm2_name, is_taker_fee=True),
                "maker_fee": Global.read_market_fee(mm2_name, is_taker_fee=False),
                "min_trading_coin": Global.read_min_trading_coin(mm2_name, target_currency),
                "krw_balance": 1000000,
                "coin_balance": 10

            },
            "division": division,
            "depth": depth,
            "consecution_time": consecution_time,
            "start_time": start_time,
            "end_time": end_time
        }

    @staticmethod
    def get_bal_fact_settings(krw_seq_end: float, coin_seq_end: float):
        """
        :return:
        only need to config krw b/c COIN bal_fact_setting will be automatically adjusted
        by real_time exchange rate calc in IBO

        """
        krw_step_limit = 1000

        return {
            "mm1": {
                "krw_balance": {"start": 0, "end": krw_seq_end, "step_limit": krw_step_limit
                                },
                "coin_balance": {"start": 0, "end": coin_seq_end, "step_limit": 0.1
                                 }
            },
            "mm2": {
                "krw_balance": {"start": 0, "end": krw_seq_end, "step_limit": krw_step_limit
                                },
                "coin_balance": {"start": 0, "end": coin_seq_end, "step_limit": 0.1
                                 }
            }
        }

    @staticmethod
    def get_factor_settings(max_trade_coin_end: float, threshold_end: int, appx_unit_coin_price: int):

        trading_coin_limit = (1000 / appx_unit_coin_price)

        return {
            "max_trading_coin": {"start": 0, "end": max_trade_coin_end, "step_limit": float(trading_coin_limit)},
            "new": {
                "threshold": {"start": 0, "end": threshold_end, "step_limit": 1}
            },
            "rev": {
                "threshold": {"start": 0, "end": threshold_end, "step_limit": 1}
            }
        }
