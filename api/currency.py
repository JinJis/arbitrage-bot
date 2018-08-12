from enum import Enum


class Currency(Enum):
    pass


class CoinoneCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    QTUM = "qtum"
    LTC = "ltc"
    XRP = "xrp"

    ETC = "etc"
    IOTA = "iota"
    BTG = "btg"


class KorbitCurrency(Currency):
    BTC = "btc_krw"
    BCH = "bch_krw"
    ETH = "eth_krw"
    QTUM = "qtum_krw"
    LTC = "ltc_krw"
    XRP = "xrp_krw"

    ETC = "etc_krw"
    BTG = "btg_krw"


class GopaxCurrency(Currency):
    BTC = "BTC-KRW"
    BCH = "BCH-KRW"
    ETH = "ETH-KRW"
    QTUM = "QTUM-KRW"
    LTC = "LTC-KRW"
    XRP = "XRP-KRW"

    XLM = "XLM-KRW"


class OkcoinCurrency(Currency):
    BTC = "btc_krw"
    BCH = "bch_krw"
    ETH = "eth_krw"
    QTUM = "qtum_krw"
    LTC = "ltc_krw"
    XRP = "xrp_krw"

    ETC = "etc_krw"
    IOTA = "iota_krw"
    BTG = "btg_krw"


class CoinnestCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    QTUM = "qtum"
    LTC = "ltc"

    ETC = "etc"
    BTG = "btg"
