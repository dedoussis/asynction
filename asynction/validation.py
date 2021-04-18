from functools import wraps
from typing import Callable
from typing import Sequence

import jsonschema

from asynction.types import Operation


def validate_payload(args: Sequence, operation: Operation) -> None:
    if operation.message is None or operation.message.payload is None:
        if args:
            raise RuntimeError(
                "Args provided for operation that has no message payload defined."
            )
        # No validation needed since no message is expected
        # and no args have been provided.
        return

    schema = operation.message.payload
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


def validator_factory(operation: Operation) -> Callable:
    def decorator(handler: Callable):
        @wraps(handler)
        def handler_with_validation(*args):
            validate_payload(args, operation)
            return handler(*args)

        return handler_with_validation

    return decorator
