from enum import Enum


class Currency(Enum):
    pass


class BithumbCurrency(Currency):
    BTC = "BTC"
    BCH = "BCH"
    ETH = "ETH"
    QTUM = "QTUM"

    TRON = "TRX"
    XRP = "XRP"

    ETC = "ETC"
    BTG = "BTG"
    EOS = "EOS"


class CoinoneCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    QTUM = "qtum"

    TRON = "tron"
    XRP = "xrp"

    ETC = "etc"
    IOTA = "iota"
    BTG = "btg"


class KorbitCurrency(Currency):
    BTC = "btc_krw"
    BCH = "bch_krw"
    ETH = "eth_krw"
    QTUM = "qtum_krw"

    XRP = "xrp_krw"

    TRON = "trx_krw"
    ETC = "etc_krw"
    BTG = "btg_krw"


class GopaxCurrency(Currency):
    BTC = "BTC-KRW"
    BCH = "BCH-KRW"
    ETH = "ETH-KRW"
    QTUM = "QTUM-KRW"

    XRP = "XRP-KRW"

    TRON = "TRX-KRW"
    XLM = "XLM-KRW"


class OkcoinCurrency(Currency):
    BTC = "btc_krw"
    BCH = "bch_krw"
    ETH = "eth_krw"
    QTUM = "qtum_krw"

    XRP = "xrp_krw"
    TRON = "trx_krw"

    ETC = "etc_krw"
    IOTA = "iota_krw"
    BTG = "btg_krw"


class CoinnestCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    QTUM = "qtum"

    TRON = "tron"

    ETC = "etc"
    BTG = "btg"
