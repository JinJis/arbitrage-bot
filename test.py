import logging
from config.global_conf import Global
from trader.market_manager.okcoin_market_manager import OkcoinMarketManager, OkcoinCurrency
from trader.market_manager.bithumb_market_manager import BithumbMarketManager, BithumbCurrency


Global.configure_default_root_logging(log_level=logging.WARNING, should_log_to_file=False)
ok = OkcoinMarketManager()
bt = BithumbMarketManager()
bt.order_buy(BithumbCurrency.XRP, 200, 10)
