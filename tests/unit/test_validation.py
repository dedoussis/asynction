from typing import Mapping
from typing import Type
from unittest import mock

import pytest
from faker import Faker
from flask import Flask
from werkzeug.datastructures import ImmutableMultiDict

from asynction.exceptions import BindingsValidationException
from asynction.exceptions import PayloadValidationException
from asynction.types import ChannelBindings
from asynction.types import WebSocketsChannelBindings
from asynction.validation import bindings_validator_factory
from asynction.validation import jsonschema_validate_with_error_handling
from asynction.validation import payload_validator_factory
from asynction.validation import validate_payload
from asynction.validation import validate_request_bindings


def test_validate_payload_with_no_schema_and_no_args():
    validate_payload(args=(), schema=None)
    assert True


def test_validate_payload_with_args_but_no_defined_schema_fails(faker: Faker):
    with pytest.raises(PayloadValidationException):
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
    with pytest.raises(PayloadValidationException):
        validate_payload(
            args=[{"hello": faker.pyint()}],
            schema={"type": "object", "properties": {"hello": {"type": "string"}}},
        )


def test_validate_payload_with_single_object_schema_and_multiple_valid_args(
    faker: Faker,
):
    with pytest.raises(PayloadValidationException):
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
    with pytest.raises(PayloadValidationException):
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


def test_payload_validator_factory_invalid_args_fail_validation(faker: Faker):
    with_validation = payload_validator_factory(
        schema={
            "type": "object",
            "properties": {"hello": {"type": "string"}},
        },
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    with pytest.raises(PayloadValidationException):
        handler({"hello": faker.pyint()})


def test_validate_request_bindings_with_no_channel_bindings():
    validate_request_bindings(mock.Mock(), None)
    assert True


def test_validate_request_bindings_with_valid_request(faker: Faker):
    request = mock.Mock(
        method="GET",
        headers={
            "foo": faker.word(),
        },
        args=ImmutableMultiDict({"bar": faker.pyint()}),
    )

    bindings = ChannelBindings(
        ws=WebSocketsChannelBindings(
            method="GET",
            headers={"type": "object", "properties": {"foo": {"type": "string"}}},
            query={"type": "object", "properties": {"bar": {"type": "number"}}},
        )
    )

    validate_request_bindings(request, bindings)
    assert True


def test_validate_request_bindings_with_invalid_method_raises_bindings_validation_exc(
    faker: Faker,
):
    request = mock.Mock(
        method="GET",
        headers={
            "foo": faker.word(),
        },
        args=ImmutableMultiDict({"bar": faker.pyint()}),
    )

    bindings = ChannelBindings(
        ws=WebSocketsChannelBindings(
            method="POST",
            headers={"type": "object", "properties": {"foo": {"type": "string"}}},
            query={"type": "object", "properties": {"bar": {"type": "number"}}},
        )
    )
    with pytest.raises(BindingsValidationException):
        validate_request_bindings(request, bindings)


def test_validate_request_bindings_with_invalid_args_raises_validation_error(
    faker: Faker,
):
    request = mock.Mock(
        method="GET",
        headers={
            "foo": faker.word(),
        },
        args=ImmutableMultiDict({"bar": "not_baz"}),
    )

    bindings = ChannelBindings(
        ws=WebSocketsChannelBindings(
            method="GET",
            headers={"type": "object", "properties": {"foo": {"type": "string"}}},
            query={
                "type": "object",
                "properties": {"bar": {"type": "string", "enum": ["baz"]}},
            },
        )
    )
    with pytest.raises(BindingsValidationException):
        validate_request_bindings(request, bindings)


def test_validate_request_bindings_with_invalid_headers_raises_validation_error(
    faker: Faker,
):
    request = mock.Mock(
        method="GET",
        headers={
            "foo": "not_baz",
        },
        args=ImmutableMultiDict({"bar": faker.pyint()}),
    )

    bindings = ChannelBindings(
        ws=WebSocketsChannelBindings(
            method="GET",
            headers={
                "type": "object",
                "properties": {"foo": {"type": "string", "enum": ["baz"]}},
            },
            query={"type": "object", "properties": {"bar": {"type": "number"}}},
        )
    )
    with pytest.raises(BindingsValidationException):
        validate_request_bindings(request, bindings)


def test_bindings_validator_factory_validates_valid_request_successfully(faker: Faker):
    with_validation = bindings_validator_factory(
        bindings=ChannelBindings(
            ws=WebSocketsChannelBindings(
                headers={
                    "type": "object",
                    "properties": {"foo": {"type": "string", "enum": ["baz"]}},
                }
            )
        ),
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    with Flask(__name__).test_client() as c:
        c.get(headers={"foo": "baz"})
        handler({"hello": faker.word()})


def test_bindings_validator_factory_invalid_request_fails_validation(faker: Faker):

    with_validation = bindings_validator_factory(
        bindings=ChannelBindings(
            ws=WebSocketsChannelBindings(
                headers={
                    "type": "object",
                    "properties": {"foo": {"type": "string", "enum": ["baz"]}},
                }
            )
        ),
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    with Flask(__name__).test_client() as c:
        c.get(headers={"foo": "not_baz"})
        with pytest.raises(BindingsValidationException):
            handler({"hello": faker.word()})


@pytest.mark.parametrize(
    argnames=["exc_type"],
    argvalues=[
        [PayloadValidationException],
        [BindingsValidationException],
        [ZeroDivisionError],
    ],
    ids=["payload_validation_exc", "bindings_validation_exc", "random_exc"],
)
def test_jsonschema_validate_with_error_handling_uses_given_exc_type(
    exc_type: Type[Exception], faker: Faker
):
    with pytest.raises(exc_type):
        jsonschema_validate_with_error_handling(
            faker.pyint(), {"type": "string"}, exc_type
        )
