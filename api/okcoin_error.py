from enum import Enum


class OkcoinErrorCode(Enum):
    RequieredField = (10000, "Required field, can not be null")
    RequestFreqExceed = (10001, "Request frequency too high to exceed the limit allowed")
    SystemError = (10002, "System error")
    NullinReqList = (10003, "Not in reqest list, please try again later")
    BlockedIP = (10004, "This IP is not allowed to access")
    SecretKeyInvalid = (10005, "'SecretKey' does not exist")
    APIKeyInvalid = (10006, "'Api_key' does not exist")
    SignatureFailed = (10007, "Signature does not match")
    IllegalParam = (10008, "Illegal parameter")
    OrderNotExist = (10009, "Order does not exist")
    InsufficientAsset = (10010, "Insufficient funds")
    AmtTooLow = (10011, "Amount too low")
    OnlyBTCLTC = (10012, "Only btc_krw ltc_krw supported")
    OnlyHttpRequest = (10013, "Only support https request")
    OrderPriceError = (10014, "Order price must be between 0 and 1,000,000")
    OrderPriceDiff = (10015, "Order price differs from current market price too much")
    InsufficientCoin = (10016, "Insufficient coins balance")
    APIAuthenError = (10017, "API authorization error")
    TooLowQuantity = (10018, "borrow amount less than lower limit [krw:100,btc:0.1,ltc:1]")
    LoanCheckError = (10019, "loan agreement not checked")
    RateExceed = (10020, "rate cannot exceed 1%")
    RateInsufficient = (10021, "rate cannot less than 0.01%")
    LatestTickerFail = (10023, "fail to get latest ticker")
    BalanceLow = (10024, "balance not sufficient")
    QuotaExceeded = (10025, "quota is full, cannot borrow temporarily")
    LoanWithdrawFailed = (10026, "Loan (including reserved loan) and margin cannot be withdrawn")
    WithdrawFailBeforeAuthen = (10027, "Cannot withdraw within 24 hrs of authentication information modification")
    WithdrawLimitReached = (10028, "Withdrawal amount exceeds daily limit")
    PayOffLoan = (10029, "Account has unpaid loan, please cancel/pay off the loan before withdraw")
    NetworkFeeTooHigh = (10033, "Fee higher than maximum network transaction fee")
    NetworkFeeTooLow = (10034, "Fee lower than minimum network transaction fee")

    def __new__(cls, *args, **kwargs):
        # manually create singleton enum member
        obj = object.__new__(cls)
        # args will be the tuple on each member
        # save the code as the actual enum value
        obj._value_ = args[0]
        # save the message as singleton's attribute
        obj.message = args[1]
        return obj


class OkcoinError(RuntimeError):
    def __init__(self, error_code: int, error_msg: str):
        try:
            _error_code = OkcoinErrorCode(error_code)
            super().__init__("\"%s\" (code %s)" % (_error_code.message, _error_code.value))
        except:
            super().__init__("\"%s\" (code %s)" % (error_msg, error_code))
