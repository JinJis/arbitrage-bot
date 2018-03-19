from api.coinone_api import CoinoneApi
from api.currency import CoinoneCurrency
from datetime import datetime
import logging


def coinone_private_api_test():
    coinone_api = CoinoneApi()
    # print(coinone_api.get_balance())
    print(coinone_api.get_ticker(CoinoneCurrency.ETH))
    # print()


# coinone_private_api_test()

# from datetime import datetime
#
a = datetime(2018, 3, 14, 12, 0, 0)
b = datetime.today()
#
# print(a)
print(b)
# print((b - a).seconds (b - a).seconds / 60 / 60)

# logger = logging.getLogger("test")
# logger.setLevel(logging.DEBUG)
# ch = logging.StreamHandler()
# ch.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
# logger.addHandler(ch)
# logger.info("hello")
#
# logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
# logging.info("hello")
