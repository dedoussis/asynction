"""Asynction's exceptions to be caught via Flask-SocketIO error handlers."""


class AsynctionException(RuntimeError):
    """The base class for all asynction runtime exceptions."""

    pass


class ValidationException(AsynctionException):
    """The base class for all asynction validation exceptions."""

    pass


class PayloadValidationException(ValidationException):
    """
    Raised when the payload of an incoming or outgoing message
    fails the schema validation.
    """

    pass


class BindingsValidationException(ValidationException):
    """
    Raised when the HTTP bindings of an incoming connection
    fail the schema validation.
    """

    pass


class MessageAckValidationException(ValidationException):
    """
    Raised when the input arguments passed to the ack callback
    do not adhere to the ``x-ack`` args schema.
    """

    pass
