from enum import Enum


class Currency(Enum):
    pass


class CoinoneCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    ETC = "etc"
    XRP = "xrp"
    QTUM = "qtum"
    IOTA = "iota"
    LTC = "ltc"
    BTG = "btg"


class KorbitCurrency(Currency):
    BTC = "btc_krw"
    BCH = "bch_krw"
    ETH = "eth_krw"
    ETC = "etc_krw"
    XRP = "xrp_krw"


class VirtualCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    ETC = "etc"
    XRP = "xrp"
    QTUM = "qtum"
    IOTA = "iota"
    LTC = "ltc"
    BTG = "btg"
