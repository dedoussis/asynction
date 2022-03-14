from typing import Mapping
from typing import Sequence
from typing import Type
from unittest import mock

import pytest
from faker import Faker
from flask import Flask
from werkzeug.datastructures import ImmutableMultiDict

from asynction.exceptions import BindingsValidationException
from asynction.exceptions import MessageAckValidationException
from asynction.exceptions import PayloadValidationException
from asynction.exceptions import ValidationException
from asynction.types import ChannelBindings
from asynction.types import Message
from asynction.types import MessageAck
from asynction.types import WebSocketsChannelBindings
from asynction.utils import Decorator
from asynction.validation import bindings_validator_factory
from asynction.validation import callback_validator_factory
from asynction.validation import jsonschema_validate_with_custom_error
from asynction.validation import publish_message_validator_factory
from asynction.validation import validate_ack_args
from asynction.validation import validate_payload
from asynction.validation import validate_request_bindings


@pytest.mark.parametrize(
    argnames=["args"],
    argvalues=[("foo",), (tuple(),)],
    ids=["with_args", "with_no_args"],
)
def test_validate_payload_with_no_schema(args: Sequence):
    validate_payload(args=args, schema=None)
    assert True


def test_validate_payload_with_args_but_no_defined_schema_is_skipped(faker: Faker):
    validate_payload(args=faker.pytuple(), schema=None)
    assert True


def test_validate_payload_with_single_object_schema_and_single_valid_arg(
    faker: Faker,
):
    validate_payload(
        args=({"hello": faker.pystr()},),
        schema={"type": "object", "properties": {"hello": {"type": "string"}}},
    )
    assert True


def test_validate_payload_with_single_object_schema_and_single_invalid_arg(
    faker: Faker,
):
    with pytest.raises(PayloadValidationException):
        validate_payload(
            args=({"hello": faker.pyint()},),
            schema={"type": "object", "properties": {"hello": {"type": "string"}}},
        )


def test_validate_payload_with_single_object_schema_and_multiple_valid_args(
    faker: Faker,
):
    with pytest.raises(PayloadValidationException):
        validate_payload(
            args=tuple(
                [{"hello": faker.pystr()}] * faker.pyint(min_value=2, max_value=10)
            ),
            schema={
                "type": "object",
                "properties": {"hello": {"type": "string"}},
            },
        )


def test_validate_payload_with_array_schema_and_single_valid_arg(
    faker: Faker,
):
    validate_payload(
        args=(faker.pylist(value_types=[str]),),
        schema={
            "type": "array",
            "items": {"type": "string"},
        },
    )
    assert True


def test_validate_payload_with_array_schema_and_single_invalid_arg(
    faker: Faker,
):
    with pytest.raises(PayloadValidationException):
        validate_payload(
            args=(faker.pylist(value_types=[int]),),
            schema={
                "type": "array",
                "items": {"type": "string"},
            },
        )
        assert True


def test_validate_payload_with_tuple_schema_and_multiple_valid_args(
    faker: Faker,
):
    validate_payload(
        args=({"hello": faker.pystr()}, faker.pyint()),
        schema={
            "type": "array",
            "prefixItems": [
                {"type": "object", "properties": {"hello": {"type": "string"}}},
                {"type": "number"},
            ],
        },
    )
    assert True


def test_validate_payload_with_tuple_schema_and_multiple_invalid_args(
    faker: Faker,
):
    with pytest.raises(PayloadValidationException):
        validate_payload(
            args=({"hello": faker.pystr()}, faker.pyint()),
            schema={
                "type": "array",
                "prefixItems": [
                    {
                        "type": "object",
                        "properties": {"hello": {"type": "string"}},
                    },
                    {"type": "string"},
                ],
            },
        )


@pytest.mark.parametrize(
    argnames=["args"],
    argvalues=[("foo",), (tuple(),)],
    ids=["with_args", "with_no_args"],
)
def test_validate_ack_args_with_no_schema(args: Sequence):
    validate_ack_args(args=args, message_ack_spec=None)
    assert True


def test_validate_ack_args_with_single_object_schema_and_single_valid_arg(
    faker: Faker,
):
    validate_ack_args(
        ({"hello": faker.pystr()},),
        MessageAck(
            args={"type": "object", "properties": {"hello": {"type": "string"}}}
        ),
    )
    assert True


def test_validate_ack_args_with_single_object_schema_and_single_invalid_arg(
    faker: Faker,
):
    with pytest.raises(MessageAckValidationException):
        validate_ack_args(
            ({"hello": faker.pyint()},),
            MessageAck(
                args={"type": "object", "properties": {"hello": {"type": "string"}}}
            ),
        )


def test_validate_ack_args_with_single_object_schema_and_multiple_valid_args(
    faker: Faker,
):
    with pytest.raises(MessageAckValidationException):
        validate_ack_args(
            tuple([{"hello": faker.pystr()}] * faker.pyint(min_value=2, max_value=10)),
            MessageAck(
                args={
                    "type": "object",
                    "properties": {"hello": {"type": "string"}},
                }
            ),
        )


def test_validate_ack_args_with_array_schema_and_single_valid_arg(
    faker: Faker,
):
    validate_ack_args(
        (faker.pylist(value_types=[str]),),
        MessageAck(
            args={
                "type": "array",
                "items": {"type": "string"},
            }
        ),
    )
    assert True


def test_validate_ack_args_with_array_schema_and_single_invalid_arg(
    faker: Faker,
):
    with pytest.raises(MessageAckValidationException):
        validate_ack_args(
            (faker.pylist(value_types=[int]),),
            MessageAck(
                args={
                    "type": "array",
                    "items": {"type": "string"},
                }
            ),
        )
        assert True


def test_validate_ack_args_with_tuple_schema_and_multiple_valid_args(
    faker: Faker,
):
    validate_ack_args(
        ({"hello": faker.pystr()}, faker.pyint()),
        MessageAck(
            args={
                "type": "array",
                "prefixItems": [
                    {"type": "object", "properties": {"hello": {"type": "string"}}},
                    {"type": "number"},
                ],
            }
        ),
    )
    assert True


def test_validate_ack_args_with_tuple_schema_and_multiple_invalid_args(
    faker: Faker,
):
    with pytest.raises(MessageAckValidationException):
        validate_ack_args(
            ({"hello": faker.pystr()}, faker.pyint()),
            MessageAck(
                args={
                    "type": "array",
                    "prefixItems": [
                        {
                            "type": "object",
                            "properties": {"hello": {"type": "string"}},
                        },
                        {"type": "string"},
                    ],
                }
            ),
        )


def test_publish_message_validator_factory_validates_valid_args_and_acks_successfully(
    faker: Faker,
):
    with_validation: Decorator = publish_message_validator_factory(
        message=Message(
            name=faker.word(),
            payload={
                "type": "object",
                "properties": {"hello": {"type": "string"}},
            },
            x_ack=MessageAck(
                args={
                    "type": "object",
                    "properties": {"acknowledged": {"type": "string"}},
                    "required": ["acknowledged"],
                }
            ),
        )
    )

    @with_validation
    def handler(message: Mapping) -> Mapping[str, str]:
        assert "hello" in message
        return {"acknowledged": faker.pystr()}

    handler({"hello": faker.pystr()})
    assert True


def test_publish_message_validato_factory_invalid_args_fail_payload_validation(
    faker: Faker,
):
    with_validation: Decorator = publish_message_validator_factory(
        message=Message(
            name=faker.word(),
            payload={
                "type": "object",
                "properties": {"hello": {"type": "string"}},
            },
        ),
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    with pytest.raises(PayloadValidationException):
        handler({"hello": faker.pyint()})


def test_publish_message_validator_factory_invalid_ack_fails_validation(
    faker: Faker,
):
    with_validation: Decorator = publish_message_validator_factory(
        message=Message(
            name=faker.word(),
            payload={
                "type": "object",
                "properties": {"hello": {"type": "string"}},
            },
            x_ack=MessageAck(
                args={
                    "type": "object",
                    "properties": {"acknowledged": {"type": "string"}},
                    "required": ["acknowledged"],
                }
            ),
        )
    )

    @with_validation
    def handler(message: Mapping) -> Mapping[str, str]:
        assert "hello" in message
        return {"not-acknowledged": faker.pystr()}

    with pytest.raises(MessageAckValidationException):
        handler({"hello": faker.pystr()})


def test_publish_message_validator_factory_skips_ack_validation_if_handler_returns_none(
    faker: Faker,
):
    with_validation: Decorator = publish_message_validator_factory(
        message=Message(
            name=faker.word(),
            payload={
                "type": "object",
                "properties": {"hello": {"type": "string"}},
            },
            x_ack=MessageAck(
                args={
                    "type": "object",
                    "properties": {"acknowledged": {"type": "string"}},
                    "required": ["acknowledged"],
                }
            ),
        )
    )

    @with_validation
    def handler(message: Mapping) -> None:
        assert "hello" in message

    handler({"hello": faker.pystr()})
    assert True


def test_publish_message_validator_factory_skips_ack_validation_if_no_ack_schema(
    faker: Faker,
):
    with_validation: Decorator = publish_message_validator_factory(
        message=Message(
            name=faker.word(),
            payload={
                "type": "object",
                "properties": {"hello": {"type": "string"}},
            },
            x_ack=None,
        )
    )

    @with_validation
    def handler(message: Mapping) -> Mapping[str, str]:
        assert "hello" in message
        return {"not-acknowledged": faker.pystr()}

    handler({"hello": faker.pystr()})
    assert True


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
    with_validation: Decorator = bindings_validator_factory(
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

    with_validation: Decorator = bindings_validator_factory(
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
        [ValidationException],
    ],
    ids=["payload_validation_exc", "bindings_validation_exc", "super_validation_exc"],
)
def test_jsonschema_validate_with_custom_error_uses_given_exc_type(
    exc_type: Type[ValidationException], faker: Faker
):
    with pytest.raises(exc_type):
        jsonschema_validate_with_custom_error(
            faker.pyint(), {"type": "string"}, exc_type
        )


def test_callback_validator_factory_validates_valid_callback_args_successfully(
    faker: Faker,
):
    with_validation: Decorator = callback_validator_factory(
        message=Message(
            name=faker.word(),
            x_ack=MessageAck(
                args={
                    "type": "object",
                    "properties": {"acknowledged": {"type": "string"}},
                    "required": ["acknowledged"],
                }
            ),
        )
    )

    @with_validation
    def callback(message: Mapping) -> None:
        assert "acknowledged" in message

    callback({"acknowledged": faker.pystr()})
    assert True


def test_callback_validator_factory_invalid_callback_args_fail_validation(
    faker: Faker,
):
    with_validation: Decorator = callback_validator_factory(
        message=Message(
            name=faker.word(),
            x_ack=MessageAck(
                args={
                    "type": "object",
                    "properties": {"acknowledged": {"type": "string"}},
                    "required": ["acknowledged"],
                }
            ),
        )
    )

    @with_validation
    def callback(message: Mapping) -> None:
        assert "not-acknowledged" in message

    with pytest.raises(MessageAckValidationException):
        callback({"not-acknowledged": faker.pystr()})
