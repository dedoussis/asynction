from functools import wraps
from typing import Callable
from typing import Optional
from typing import Sequence

import jsonschema

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
