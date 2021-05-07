class AsynctionException(RuntimeError):
    pass


class ValidationException(AsynctionException):
    pass


class PayloadValidationException(ValidationException):
    pass


class BindingsValidationException(ValidationException):
    pass
