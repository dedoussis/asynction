from functools import wraps
from typing import Callable
from typing import Optional
from typing import Sequence

import jsonschema
from flask import Request
from flask import request as current_flask_request

from asynction.types import ChannelBindings
from asynction.types import JSONSchema


def validate_payload(args: Sequence, schema: Optional[JSONSchema]) -> None:
    if schema is None:
        if args:
            raise RuntimeError(
                "Args provided for operation that has no message payload defined."
            )
        # No validation needed since no message is expected
        # and no args have been provided.
        return

    schema_type = schema["type"]
    if schema_type == "array":
        jsonschema.validate(args, schema)
    else:
        if len(args) > 1:
            raise RuntimeError(
                "Multiple handler arguments provided, "
                f"although schema type is: {schema_type}"
            )
        jsonschema.validate(args[0], schema)


def payload_validator_factory(schema: Optional[JSONSchema]) -> Callable:
    def decorator(handler: Callable):
        @wraps(handler)
        def handler_with_validation(*args):
            validate_payload(args, schema)
            return handler(*args)

        return handler_with_validation

    return decorator


def validate_request_bindings(
    request: Request, bindings: Optional[ChannelBindings]
) -> None:
    if bindings is None:
        # No validation needed since there are no bindings defined
        return

    if bindings.ws.method is not None and request.method != bindings.ws.method:
        raise RuntimeError(
            "Binding validation failed. "
            f"Request method {request.method} does not match {bindings.ws.method}."
        )

    if bindings.ws.headers is not None:
        jsonschema.validate(
            {k.lower(): v for k, v in request.headers.items()}, bindings.ws.headers
        )

    if bindings.ws.query is not None:
        jsonschema.validate(request.args.to_dict(), bindings.ws.query)


def bindings_validator_factory(bindings: Optional[ChannelBindings]) -> Callable:
    def decorator(handler: Callable):
        @wraps(handler)
        def handler_with_validation(*args):
            validate_request_bindings(current_flask_request, bindings)
            return handler(*args)

        return handler_with_validation

    return decorator
