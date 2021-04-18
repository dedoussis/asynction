from typing import Mapping

import jsonschema
import pytest
from faker import Faker

from asynction.types import Message
from asynction.types import Operation
from asynction.validation import validate_payload
from asynction.validation import validator_factory


def test_validate_payload_with_no_defined_message_and_empty_args():
    validate_payload(args=(), operation=Operation())
    assert True


def test_validate_payload_with_no_defined_message_and_args_fails(faker: Faker):
    with pytest.raises(RuntimeError):
        validate_payload(args=faker.pylist(), operation=Operation())


def test_validate_payload_with_defined_message_object_and_valid_single_arg(
    faker: Faker,
):
    validate_payload(
        args=[{"hello": faker.pystr()}],
        operation=Operation(
            message=Message(
                payload={"type": "object", "properties": {"hello": {"type": "string"}}}
            )
        ),
    )
    assert True


def test_validate_payload_with_defined_message_object_and_single_invalid_arg(
    faker: Faker,
):
    with pytest.raises(jsonschema.ValidationError):
        validate_payload(
            args=[{"hello": faker.pyint()}],
            operation=Operation(
                message=Message(
                    payload={
                        "type": "object",
                        "properties": {"hello": {"type": "string"}},
                    }
                )
            ),
        )


def test_validate_payload_with_defined_message_object_and_multiple_valid_args(
    faker: Faker,
):
    with pytest.raises(RuntimeError):
        validate_payload(
            args=[{"hello": faker.pystr()}] * faker.pyint(min_value=2, max_value=10),
            operation=Operation(
                message=Message(
                    payload={
                        "type": "object",
                        "properties": {"hello": {"type": "string"}},
                    }
                )
            ),
        )


def test_validate_payload_with_defined_message_array_and_multiple_valid_args(
    faker: Faker,
):
    validate_payload(
        args=[{"hello": faker.pystr()}, faker.pyint()],
        operation=Operation(
            message=Message(
                payload={
                    "type": "array",
                    "items": [
                        {"type": "object", "properties": {"hello": {"type": "string"}}},
                        {"type": "number"},
                    ],
                }
            )
        ),
    )
    assert True


def test_validate_payload_with_defined_message_array_and_multiple_invalidvalid_args(
    faker: Faker,
):
    with pytest.raises(jsonschema.ValidationError):
        validate_payload(
            args=[{"hello": faker.pystr()}, faker.pyint()],
            operation=Operation(
                message=Message(
                    payload={
                        "type": "array",
                        "items": [
                            {
                                "type": "object",
                                "properties": {"hello": {"type": "string"}},
                            },
                            {"type": "string"},
                        ],
                    }
                )
            ),
        )


def test_validator_factory_validates_valid_args_successfully(faker: Faker):
    with_validation = validator_factory(
        Operation(
            message=Message(
                payload={
                    "type": "object",
                    "properties": {"hello": {"type": "string"}},
                }
            )
        )
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    handler({"hello": faker.pystr()})


def test_validator_factory_fails_to_validate_invalid_args(faker: Faker):
    with_validation = validator_factory(
        Operation(
            message=Message(
                payload={
                    "type": "object",
                    "properties": {"hello": {"type": "string"}},
                }
            )
        )
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    with pytest.raises(jsonschema.ValidationError):
        handler({"hello": faker.pyint()})
