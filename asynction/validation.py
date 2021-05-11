from functools import partial
from functools import wraps
from typing import Callable
from typing import Optional
from typing import Sequence
from typing import Type

import jsonschema
from flask import Request
from flask import request as current_flask_request

from asynction.exceptions import BindingsValidationException
from asynction.exceptions import MessageAckValidationException
from asynction.exceptions import PayloadValidationException
from asynction.types import ChannelBindings
from asynction.types import JSONMapping
from asynction.types import JSONSchema
from asynction.types import Message
from asynction.types import MessageAck


def jsonschema_validate_with_error_handling(
    instance: JSONMapping, schema: JSONSchema, exc_type: Type[Exception]
) -> None:
    try:
        jsonschema.validate(instance, schema)
    except jsonschema.ValidationError as e:
        raise exc_type(str(e))


jsonschema_validate_payload = partial(
    jsonschema_validate_with_error_handling,
    exc_type=PayloadValidationException,
)

jsonschema_validate_bindings = partial(
    jsonschema_validate_with_error_handling, exc_type=BindingsValidationException
)

jsonschema_validate_ack = partial(
    jsonschema_validate_with_error_handling, exc_type=MessageAckValidationException
)


def validate_payload(args: Sequence, schema: Optional[JSONSchema]) -> None:
    if schema is None:
        if args:
            raise PayloadValidationException(
                "Handler args provided for message that has no payload defined."
            )
        # Validation succeeded since there is no message payload specified
        # and no args have been provided.
        return

    schema_type = schema["type"]
    if schema_type == "array":
        jsonschema_validate_payload(args, schema)
    else:
        if len(args) > 1:
            raise PayloadValidationException(
                "Multiple handler arguments provided, "
                f"although schema type is: {schema_type}"
            )

        jsonschema_validate_payload(args[0], schema)


def validate_ack_args(args: Sequence, message_ack_spec: Optional[MessageAck]) -> None:
    if message_ack_spec is None:
        if args:
            raise MessageAckValidationException(
                "Callback args provided for message that has no x-ack schema specified."
            )
        # Validation succeeded since there is no message ack specified
        # and no args have been provided.
        return

    schema_type = message_ack_spec.args["type"]
    if schema_type == "array":
        jsonschema_validate_ack(args, message_ack_spec.args)
    else:
        if len(args) > 1:
            raise MessageAckValidationException(
                "Multiple callback arguments provided, "
                f"although x-ack schema type is: {schema_type}"
            )

        jsonschema_validate_ack(args[0], message_ack_spec.args)


def publish_message_validator_factory(message: Message) -> Callable:
    """Constructs a validating wrapper for any incoming (`publish`) message handler"""

    def decorator(handler: Callable):
        @wraps(handler)
        def handler_with_validation(*args):
            validate_payload(args, message.payload)

            ack = handler(*args)

            if ack is not None and message.x_ack is not None:
                jsonschema_validate_ack(ack, message.x_ack.args)

            return ack

        return handler_with_validation

    return decorator


def callback_validator_factory(message: Message) -> Callable:
    def decorator(callback: Callable):
        @wraps(callback)
        def callback_with_validation(*args):
            # the callback should only be called with positional arguments
            validate_ack_args(args, message.x_ack)
            return callback(*args)

        return callback_with_validation

    return decorator


def validate_request_bindings(
    request: Request, bindings: Optional[ChannelBindings]
) -> None:
    if bindings is None:
        # No validation needed since there are no bindings defined
        return

    if bindings.ws.method is not None and request.method != bindings.ws.method:
        raise BindingsValidationException(
            "Binding validation failed. "
            f"Request method {request.method} does not match {bindings.ws.method}."
        )

    if bindings.ws.headers is not None:
        jsonschema_validate_bindings(
            {k.lower(): v for k, v in request.headers.items()}, bindings.ws.headers
        )

    if bindings.ws.query is not None:
        jsonschema_validate_bindings(request.args.to_dict(), bindings.ws.query)


def bindings_validator_factory(bindings: Optional[ChannelBindings]) -> Callable:
    def decorator(handler: Callable):
        @wraps(handler)
        def handler_with_validation(*args):
            validate_request_bindings(current_flask_request, bindings)
            return handler(*args)

        return handler_with_validation

    return decorator
