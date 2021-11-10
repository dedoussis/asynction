from asynction.exceptions import AsynctionException


class SecurityException(AsynctionException):
    """
    Base Security Exception type.
    """
    pass


class UnregisteredSecurityScheme(SecurityException):
    """
    Raised when a security scheme not listed in the securitySchemes section of the
    spec is used in a ``security`` or ``x-security`` specification
    """
    pass


class UnsupportedSecurityScheme(SecurityException):
    """
    Raised when a specified security scheme is not supported by asynction
    """
    pass
