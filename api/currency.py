from enum import Enum


class Currency(Enum):
    pass


class BithumbCurrency(Currency):
    BTC = "BTC"
    BCH = "BCH"
    ETH = "ETH"
    QTUM = "QTUM"
    TRX = "TRX"
    XRP = "XRP"
    EOS = "EOS"

    ETC = "ETC"
    BTG = "BTG"


class CoinoneCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    QTUM = "qtum"
    EOS = "eos"

    XRP = "xrp"

    ETC = "etc"
    IOTA = "iota"
    BTG = "btg"


class KorbitCurrency(Currency):
    BTC = "btc_krw"
    BCH = "bch_krw"
    ETH = "eth_krw"
    QTUM = "qtum_krw"
    EOS = "eos_krw"

    XRP = "xrp_krw"

    TRX = "trx_krw"
    ETC = "etc_krw"
    BTG = "btg_krw"


class GopaxCurrency(Currency):
    BTC = "BTC-KRW"
    BCH = "BCH-KRW"
    ETH = "ETH-KRW"
    QTUM = "QTUM-KRW"
    EOS = "EOS-KRW"
    XRP = "XRP-KRW"

    TRX = "TRX-KRW"
    XLM = "XLM-KRW"


class OkcoinCurrency(Currency):
    BTC = "btc_krw"
    BCH = "bch_krw"
    ETH = "eth_krw"
    QTUM = "qtum_krw"
    XRP = "xrp_krw"
    EOS = "eos_krw"

    TRX = "trx_krw"

    ETC = "etc_krw"
    IOTA = "iota_krw"
    BTG = "btg_krw"


class CoinnestCurrency(Currency):
    BTC = "btc"
    BCH = "bch"
    ETH = "eth"
    QTUM = "qtum"

    TRX = "tron"

    ETC = "etc"
    BTG = "btg"
