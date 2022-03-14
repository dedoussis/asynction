from functools import partial
from functools import wraps
from typing import Any
from typing import Optional
from typing import Sequence
from typing import Type
from typing import TypeVar

import jsonschema
from flask import Request
from flask import request as current_flask_request

from asynction.exceptions import BindingsValidationException
from asynction.exceptions import MessageAckValidationException
from asynction.exceptions import PayloadValidationException
from asynction.exceptions import ValidationException
from asynction.types import ChannelBindings
from asynction.types import JSONMapping
from asynction.types import JSONSchema
from asynction.types import Message
from asynction.types import MessageAck
from asynction.utils import Decorator
from asynction.utils import Func


def jsonschema_validate_with_custom_error(
    instance: JSONMapping, schema: JSONSchema, exc_type: Type[ValidationException]
) -> None:
    try:
        jsonschema.validate(instance, schema)
    except jsonschema.ValidationError as e:
        raise exc_type.create_from(e)


jsonschema_validate_payload = partial(
    jsonschema_validate_with_custom_error,
    exc_type=PayloadValidationException,
)

jsonschema_validate_bindings = partial(
    jsonschema_validate_with_custom_error, exc_type=BindingsValidationException
)

jsonschema_validate_ack = partial(
    jsonschema_validate_with_custom_error, exc_type=MessageAckValidationException
)


def validate_payload(args: Sequence, schema: Optional[JSONSchema]) -> None:
    if schema is None:
        # Validation skipped since there is no message payload specified
        return

    # TODO: This check should be driven by the schema rather than the input args
    if len(args) > 1:
        jsonschema_validate_payload(list(args), schema)
    else:
        jsonschema_validate_payload(args[0], schema)


def validate_ack_args(args: Sequence, message_ack_spec: Optional[MessageAck]) -> None:
    if message_ack_spec is None:
        # Validation skipped since there is no message ack specified
        return

    # TODO: This check should be driven by the schema rather than the input args
    if len(args) > 1:
        jsonschema_validate_ack(list(args), message_ack_spec.args)
    else:
        jsonschema_validate_ack(args[0], message_ack_spec.args)


T = TypeVar("T")


def publish_message_validator_factory(message: Message) -> Decorator[T]:
    """Constructs a validating wrapper for any incoming (`publish`) message handler"""

    def decorator(handler: Func[T]) -> Func[T]:
        @wraps(handler)
        def handler_with_validation(*args: Any, **kwargs: Any) -> T:
            validate_payload(args, message.payload)

            ack = handler(*args, **kwargs)

            if ack is not None and message.x_ack is not None:
                jsonschema_validate_ack(ack, message.x_ack.args)

            # TODO: Should the ack be transmitted if there is no x-ack definition?
            return ack

        return handler_with_validation

    return decorator


def callback_validator_factory(message: Message) -> Decorator[T]:
    def decorator(callback: Func[T]) -> Func[T]:
        @wraps(callback)
        def callback_with_validation(*args: Any) -> T:
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


def bindings_validator_factory(bindings: Optional[ChannelBindings]) -> Decorator[T]:
    def decorator(handler: Func[T]) -> Func[T]:
        @wraps(handler)
        def handler_with_validation(*args: Any, **kwargs: Any) -> T:
            validate_request_bindings(current_flask_request, bindings)
            return handler(*args, **kwargs)

        return handler_with_validation

    return decorator
