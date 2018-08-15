from trader.market.market import Market
from config.global_conf import Global


class TradeSettingConfig:

    @staticmethod
    def get_settings(mm1: str, mm2: str, target_currency: str, start_time: int, end_time: int, division: str,
                     depth: str, consecution_time: str, is_virtual_mm: bool):
        if is_virtual_mm:
            mm1_tag = "VIRTUAL_%s" % mm1.upper()
            mm2_tag = "VIRTUAL_%s" % mm2.upper()
        elif not is_virtual_mm:
            mm1_tag = mm1.upper()
            mm2_tag = mm2.upper()
        else:
            raise Exception("Please type mm1 and mm2 correctly! ex) coinone")

        return {
            "target_currency": target_currency,
            "mm1": {
                "market_tag": getattr(Market, mm1_tag),
                "taker_fee": Global.read_market_fee(mm1, is_taker_fee=True),
                "maker_fee": Global.read_market_fee(mm1, is_taker_fee=False),
                "krw_balance": 1000000,
                "coin_balance": 10
            },
            "mm2": {
                "market_tag": getattr(Market, mm2_tag),
                "taker_fee": Global.read_market_fee(mm2, is_taker_fee=True),
                "maker_fee": Global.read_market_fee(mm2, is_taker_fee=False),
                "krw_balance": 1000000,
                "coin_balance": 10

            },
            "division": int(division),
            "depth": int(depth),
            "consecution_time": int(consecution_time),
            "start_time": start_time,
            "end_time": end_time
        }

    @staticmethod
    def get_bal_fact_settings(krw_seq_end: str):
        """
        :return:
        only need to config krw b/c COIN bal_fact_setting will be automatically adjusted
        by real_time exchange rate calc in IBO

        """
        krw_step_limit = 1000

        return {
            "mm1": {
                "krw_balance": {"start": 0, "end": float(krw_seq_end), "step_limit": krw_step_limit
                                },
                "coin_balance": {"start": 0, "end": 10, "step_limit": 0.1
                                 }
            },
            "mm2": {
                "krw_balance": {"start": 0, "end": float(krw_seq_end), "step_limit": krw_step_limit
                                },
                "coin_balance": {"start": 0, "end": 10, "step_limit": 0.1
                                 }
            }
        }

    @staticmethod
    def get_factor_settings(max_trade_coin_end: str, threshold_end: str, factor_end: str, appx_unit_coin_price: str):

        trading_coin_limit = (1000 / int(appx_unit_coin_price))

        return {
            "max_trading_coin": {"start": 0, "end": float(max_trade_coin_end), "step_limit": float(trading_coin_limit)},
            "min_trading_coin": {"start": 0, "end": 0, "step_limit": 0},
            "new": {
                "threshold": {"start": 0, "end": int(threshold_end), "step_limit": 1},
                "factor": {"start": 1, "end": int(factor_end), "step_limit": 0.01}
            },
            "rev": {
                "threshold": {"start": 0, "end": int(threshold_end), "step_limit": 1},
                "factor": {"start": 1, "end": int(factor_end), "step_limit": 0.01}
            }
        }
