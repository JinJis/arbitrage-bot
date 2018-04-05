from enum import Enum


class CoinoneErrorCode(Enum):
    BlockedUserAccess = (4, "Blocked user access")
    AccessTokenMissing = (11, "Access token is missing")
    InvalidAccessToken = (12, "Invalid access token")
    PermissionDenied = (40, "Invalid API permission")
    AuthenticateError = (50, "Authenticate error")
    InvalidAPI = (51, "Invalid API")
    DeprecatedAPI = (52, "Deprecated API")
    TwoFactorAuthFail = (53, "Two Factor Auth Fail")
    SessionExpired = (100, "Session expired")
    InvalidFormat = (101, "Invalid format")
    IdNotExist = (102, "ID does not exist")
    LackOfBalance = (103, "Lack of Balance")
    OrderIdNotExist104 = (104, "Order id does not exist")
    PriceIsNotCorrect = (105, "Price is not correct")
    LockingError106 = (106, "Locking error")
    ParameterError = (107, "Parameter error")
    OrderIdNotExist111 = (111, "Order id does not exist")
    CancelFailed = (112, "Cancel failed")
    TooLowQuantity = (113, "Quantity is too small(ETH, ETC > 0.01)")
    V2PayloadMissing = (120, "V2 API payload is missing")
    V2SignatureMissing = (121, "V2 API signature is missing")
    V2NonceMissing = (122, "V2 API nonce is missing")
    V2SignatureMismatch = (123, "V2 API signature is not correct")
    V2NonceNegative = (130, "V2 API Nonce value must be a positive integer")
    V2NonceMismatch = (131, "V2 API Nonce must be bigger than last nonce")
    V2BodyCorrupted = (132, "V2 API body is corrupted")
    TooManyLimitOrders = (141, "Too many limit orders")
    V1WrongAccessToken = (150, "It's V1 API. V2 Access token is not acceptable")
    V2WrongAccessToken = (151, "It's V2 API. V1 Access token is not acceptable")
    WalletError = (200, "Wallet Error")
    LimitationError202 = (202, "Limitation error")
    LimitationError210 = (210, "Limitation error")
    LimitationError220 = (220, "Limitation error")
    LimitationError221 = (221, "Limitation error")
    MobileAuthError310 = (310, "Mobile auth error")
    NeedMobileAuth = (311, "Need mobile auth")
    BadName = (312, "Name is not correct")
    BadPhoneNumber330 = (330, "Phone number error")
    PageNotFound = (404, "Page not found error")
    ServerError = (405, "Server error")
    LockingError444 = (444, "Locking error")
    EmailError500 = (500, "Email error")
    EmailError501 = (501, "Email error")
    MobileAuthError777 = (777, "Mobile auth error")
    BadPhoneNumber778 = (778, "Phone number error")
    AddressError = (779, "Address error")
    AppNotFound = (1202, "App not found")
    AlreadyRegistered = (1203, "Already registered")
    InvalidAccess = (1204, "Invalid access")
    APIKeyError = (1205, "API Key error")
    UserNotFound1206 = (1206, "User not found")
    UserNotFound1207 = (1207, "User not found")
    UserNotFound1208 = (1208, "User not found")
    UserNotFound1209 = (1209, "User not found")

    def __new__(cls, *args, **kwargs):
        # manually create singleton enum member
        obj = object.__new__(cls)
        # args will be the tuple on each member
        # save the code as the actual enum value
        obj._value_ = args[0]
        # save the message as singleton's attribute
        obj.message = args[1]
        return obj


class CoinoneError(RuntimeError):
    def __init__(self, error_code: int):
        _error_code = CoinoneErrorCode(error_code)
        super().__init__("\"%s\" (code %s)" % (_error_code.message, _error_code.value))
