from unittest import mock

import jsonschema
import pytest
from faker import Faker

from asynction.server import AsynctionSocketIO
from asynction.server import SocketIO
from asynction.server import load_handler
from asynction.server import load_spec
from asynction.server import resolve_references
from asynction.types import GLOBAL_NAMESPACE
from asynction.types import AsyncApiSpec
from asynction.types import Channel
from asynction.types import ChannelHandlers
from asynction.types import Message
from asynction.types import OneOfMessages
from asynction.types import Operation
from tests.fixtures import FixturePaths
from tests.fixtures.handlers import connect
from tests.fixtures.handlers import disconnect
from tests.fixtures.handlers import ping
from tests.fixtures.handlers import some_error
from tests.utils import deep_unwrap


def test_load_spec_instantiates_async_api_spec_object(fixture_paths: FixturePaths):
    spec = load_spec(fixture_paths.simple)
    assert isinstance(spec, AsyncApiSpec)


def test_asynction_socketio_from_spec(fixture_paths: FixturePaths):
    asio = AsynctionSocketIO.from_spec(spec_path=fixture_paths.simple)
    assert isinstance(asio, AsynctionSocketIO)


def test_resolve_references_resolves_successfully():
    raw_spec = {
        "channels": {
            "/chat": {
                "publish": {"message": {"$ref": "#/components/messages/UserMessage"}},
                "subscribe": {
                    "message": {
                        "oneOf": [
                            {"$ref": "#/components/messages/UserResponse"},
                            {"payload": {"type": "null"}},
                        ]
                    }
                },
            }
        },
        "components": {
            "messages": {
                "UserMessage": {"payload": {"type": "string"}},
                "UserResponse": {"payload": {"type": "object"}},
            },
        },
    }

    resolved = {
        "channels": {
            "/chat": {
                "publish": {
                    "message": {
                        "payload": {"type": "string"},
                    }
                },
                "subscribe": {
                    "message": {
                        "oneOf": [
                            {"payload": {"type": "object"}},
                            {"payload": {"type": "null"}},
                        ]
                    }
                },
            }
        },
        "components": {
            "messages": {
                "UserMessage": {"payload": {"type": "string"}},
                "UserResponse": {"payload": {"type": "object"}},
            },
        },
    }

    assert resolve_references(raw_spec) == resolved


def test_load_handler():
    handler_id = "tests.fixtures.handlers.ping"
    assert load_handler(handler_id) == ping


def test_register_handlers_registers_callables_with_correct_event_name_and_namespace(
    faker: Faker,
):
    namespace = f"/{faker.pystr()}"
    event_name = faker.word()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                publish=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "object"},
                                x_handler="tests.fixtures.handlers.ping",
                            )
                        ]
                    ),
                )
            )
        }
    )
    server = AsynctionSocketIO(spec)

    server._register_handlers()
    assert len(server.handlers) == 1
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == event_name
    assert deep_unwrap(registered_handler) == ping
    assert registered_namespace == namespace


def test_register_handlers_registers_channel_handlers(
    faker: Faker,
):
    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                x_handlers=ChannelHandlers(
                    connect="tests.fixtures.handlers.connect",
                    disconnect="tests.fixtures.handlers.disconnect",
                    error="tests.fixtures.handlers.some_error",
                )
            )
        }
    )
    server = AsynctionSocketIO(spec)

    server._register_handlers()

    assert server.exception_handlers[namespace] == some_error
    for event_name, handler, handler_namespace in server.handlers:
        assert handler_namespace == namespace
        unwrapped = deep_unwrap(handler)
        if event_name == "connect":
            assert unwrapped == connect
        else:
            assert unwrapped == disconnect


def test_register_handlers_adds_validator_if_validation_is_enabled(faker: Faker):
    namespace = f"/{faker.pystr()}"
    event_name = faker.word()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                publish=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "string"},
                                x_handler="tests.fixtures.handlers.ping",
                            )
                        ]
                    ),
                )
            )
        }
    )
    server = AsynctionSocketIO(spec, True)

    server._register_handlers()
    _, registered_handler, _ = server.handlers[0]
    handler_with_validation = deep_unwrap(registered_handler, depth=1)
    actual_handler = deep_unwrap(handler_with_validation)
    args = (faker.pyint(),)

    actual_handler(*args)  # actual handler does not raise validation errors
    with pytest.raises(jsonschema.ValidationError):
        handler_with_validation(*args)


def test_register_handlers_omits_validator_if_validation_is_disabled(faker: Faker):
    namespace = f"/{faker.pystr()}"
    event_name = faker.word()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                publish=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "string"},
                                x_handler="tests.fixtures.handlers.ping",
                            )
                        ]
                    ),
                )
            )
        }
    )
    server = AsynctionSocketIO(spec, False)

    server._register_handlers()
    _, registered_handler, _ = server.handlers[0]
    handler_with_validation = deep_unwrap(registered_handler, depth=1)
    actual_handler = deep_unwrap(handler_with_validation)

    assert handler_with_validation == actual_handler
    args = (faker.pyint(),)
    actual_handler(*args)  # actual handler does not raise validation errors
    assert True


def test_register_namespace_handlers_registers_global_nsp_error_handler_as_default():
    channel_handlers = ChannelHandlers(error="tests.fixtures.handlers.some_error")
    server = AsynctionSocketIO(mock.Mock())

    server._register_namespace_handlers(GLOBAL_NAMESPACE, channel_handlers)
    assert server.default_exception_handler == some_error


def test_emit_event_with_non_existent_namespace_raises_runtime_error(faker: Faker):
    namespace = f"/{faker.pystr()}"
    event_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "object"},
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(RuntimeError):
        # Correct event name but no namespace:
        server.emit(event_name, faker.pydict(value_types=[str, int]))


def test_emit_event_that_has_no_subscribe_operation_raises_runtime_error(faker: Faker):
    namespace = f"/{faker.pystr()}"
    event_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                publish=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "object"},
                                x_handler="tests.fixtures.handlers.ping",
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(RuntimeError):
        server.emit(
            event_name, faker.pydict(value_types=[str, int]), namespace=namespace
        )


def test_emit_event_not_defined_under_given_valid_namespace_raises_runtime_error(
    faker: Faker,
):
    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=faker.pystr(),
                                payload={"type": "object"},
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(RuntimeError):
        # Correct namespace but undefined event:
        server.emit(
            faker.pystr(), faker.pydict(value_types=[str, int]), namespace=namespace
        )


def test_emit_event_with_invalid_args_fails_validation(faker: Faker):
    namespace = f"/{faker.pystr()}"
    event_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "number"},
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(jsonschema.ValidationError):
        # Event args do not adhere to the schema
        server.emit(event_name, faker.pystr(), namespace=namespace)


@mock.patch.object(SocketIO, "emit")
def test_emit_valid_event_invokes_super_method(
    super_method_mock: mock.Mock, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    event_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "string"},
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = AsynctionSocketIO(spec)

    event_args = [faker.pystr()]
    server.emit(event_name, *event_args, namespace=namespace)
    super_method_mock.assert_called_once_with(
        event_name, *event_args, namespace=namespace
    )


@mock.patch.object(SocketIO, "emit")
def test_emit_validiation_is_ginored_if_validation_flag_is_false(
    super_method_mock: mock.Mock, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    event_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "number"},
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = AsynctionSocketIO(spec, validation=False)

    event_args = [faker.pystr()]  # invalid args
    server.emit(event_name, *event_args, namespace=namespace)

    # super method called because validation was skipped
    super_method_mock.assert_called_once_with(
        event_name, *event_args, namespace=namespace
    )
