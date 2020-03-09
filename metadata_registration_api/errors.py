class ApiBaseException(Exception):
    pass


class IdenticalPropertyException(ApiBaseException):
    pass


class RequestBodyException(ApiBaseException):
    pass


class TokenException(ApiBaseException):
    pass
