from typing import Mapping

import jsonschema
import pytest
from faker import Faker

from asynction.validation import payload_validator_factory
from asynction.validation import validate_payload


def test_validate_payload_with_no_schema_and_no_args():
    validate_payload(args=(), schema=None)
    assert True


def test_validate_payload_with_args_but_no_defined_schema_fails(faker: Faker):
    with pytest.raises(RuntimeError):
        validate_payload(args=faker.pylist(), schema=None)


def test_validate_payload_with_single_object_schema_and_single_valid_arg(
    faker: Faker,
):
    validate_payload(
        args=[{"hello": faker.pystr()}],
        schema={"type": "object", "properties": {"hello": {"type": "string"}}},
    )
    assert True


def test_validate_payload_with_single_object_schema_and_single_invalid_arg(
    faker: Faker,
):
    with pytest.raises(jsonschema.ValidationError):
        validate_payload(
            args=[{"hello": faker.pyint()}],
            schema={"type": "object", "properties": {"hello": {"type": "string"}}},
        )


def test_validate_payload_with_single_object_schema_and_multiple_valid_args(
    faker: Faker,
):
    with pytest.raises(RuntimeError):
        validate_payload(
            args=[{"hello": faker.pystr()}] * faker.pyint(min_value=2, max_value=10),
            schema={
                "type": "object",
                "properties": {"hello": {"type": "string"}},
            },
        )


def test_validate_payload_with_multi_object_schema_and_multiple_valid_args(
    faker: Faker,
):
    validate_payload(
        args=[{"hello": faker.pystr()}, faker.pyint()],
        schema={
            "type": "array",
            "items": [
                {"type": "object", "properties": {"hello": {"type": "string"}}},
                {"type": "number"},
            ],
        },
    )
    assert True


def test_validate_payload_with_multi_object_schema_and_multiple_invalid_args(
    faker: Faker,
):
    with pytest.raises(jsonschema.ValidationError):
        validate_payload(
            args=[{"hello": faker.pystr()}, faker.pyint()],
            schema={
                "type": "array",
                "items": [
                    {
                        "type": "object",
                        "properties": {"hello": {"type": "string"}},
                    },
                    {"type": "string"},
                ],
            },
        )


def test_payload_validator_factory_validates_valid_args_successfully(faker: Faker):
    with_validation = payload_validator_factory(
        schema={
            "type": "object",
            "properties": {"hello": {"type": "string"}},
        }
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    handler({"hello": faker.pystr()})


def test_payload_validator_factory_fails_to_validate_invalid_args(faker: Faker):
    with_validation = payload_validator_factory(
        schema={
            "type": "object",
            "properties": {"hello": {"type": "string"}},
        },
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    with pytest.raises(jsonschema.ValidationError):
        handler({"hello": faker.pyint()})
