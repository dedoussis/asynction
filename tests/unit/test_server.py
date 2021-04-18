from unittest import mock

import jsonschema
import pytest
from faker import Faker

from asynction.server import AsynctionSocketIO
from asynction.server import SocketIO
from asynction.server import load_handler
from asynction.server import load_spec
from asynction.server import resolve_references
from asynction.types import DEFAULT_NAMESPACES
from asynction.types import MAIN_NAMESPACE
from asynction.types import AsyncApiSpec
from asynction.types import Channel
from asynction.types import ChannelPath
from asynction.types import Message
from asynction.types import Namespace
from asynction.types import Operation
from tests.fixtures import FixturePaths
from tests.fixtures.handlers import my_handler
from tests.fixtures.handlers import my_other_handler
from tests.utils import deep_wrapped


def test_asynction_socketio_from_spec(fixture_paths: FixturePaths):
    asio = AsynctionSocketIO.from_spec(spec_path=fixture_paths.simple)
    assert isinstance(asio, AsynctionSocketIO)


def test_load_spec_with_simple_spec_that_specifies_no_namespaces(
    fixture_paths: FixturePaths,
):
    loaded = load_spec(spec_path=fixture_paths.simple)
    assert isinstance(loaded, AsyncApiSpec)
    assert loaded.x_namespaces == DEFAULT_NAMESPACES


def test_load_spec_with_namespaces_spec(fixture_paths: FixturePaths):
    loaded = load_spec(spec_path=fixture_paths.namespaces)
    assert isinstance(loaded, AsyncApiSpec)
    assert isinstance(loaded.x_namespaces[MAIN_NAMESPACE], Namespace)
    assert isinstance(loaded.x_namespaces["/user"], Namespace)


def test_resolve_references_resolves_successfully():
    raw_spec = {
        "channels": {
            "user/signedup": {
                "publish": {"message": {"$ref": "#/components/messages/UserSignedUp"}}
            }
        },
        "components": {"messages": {"UserSignedUp": {"type": "object"}}},
    }

    resolved = {
        "channels": {
            "user/signedup": {
                "publish": {
                    "message": {
                        "type": "object",
                    }
                }
            }
        },
        "components": {"messages": {"UserSignedUp": {"type": "object"}}},
    }

    assert resolve_references(raw_spec) == resolved


def test_load_handler():
    handler_id = "tests.fixtures.handlers.my_handler"
    assert load_handler(handler_id) == my_handler


def test_register_event_handlers_without_namespace_uses_main(
    faker: Faker,
):
    channel_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=channel_name): Channel(
                publish=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                )
            )
        }
    )
    server = AsynctionSocketIO(spec)

    server._register_event_handlers()
    assert len(server.handlers) == 1
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == channel_name
    assert deep_wrapped(registered_handler) == my_handler
    assert registered_namespace == MAIN_NAMESPACE


def test_register_event_handlers_with_namespace(
    faker: Faker,
):
    namespace = f"/{faker.pystr()}"
    channel_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=channel_name, namespace=namespace): Channel(
                publish=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
        x_namespaces={
            namespace: Namespace(),
        },
    )
    server = AsynctionSocketIO(spec)

    server._register_event_handlers()
    assert len(server.handlers) == 1
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == channel_name
    assert deep_wrapped(registered_handler) == my_handler
    assert registered_namespace == namespace


def test_register_event_handlers_raises_value_error_if_namespace_not_defined_in_defs(
    faker: Faker,
):
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=faker.pystr(), namespace=faker.pystr()): Channel(
                publish=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(ValueError):
        server._register_event_handlers()


def test_register_error_handlers_for_each_namespace(faker: Faker):
    custom_namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        channels={},
        x_namespaces={
            MAIN_NAMESPACE: Namespace(
                errorHandler="tests.fixtures.handlers.my_handler",
            ),
            custom_namespace: Namespace(
                errorHandler="tests.fixtures.handlers.my_other_handler"
            ),
        },
    )
    server = AsynctionSocketIO(spec)

    server._register_error_handlers()
    assert server.default_exception_handler == my_handler
    assert server.exception_handlers[custom_namespace] == my_other_handler


def test_emit_event_not_defined_in_spec_raises_runtime_error(faker: Faker):
    namespace = f"/{faker.pystr()}"
    channel_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=channel_name, namespace=namespace): Channel(
                subscribe=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
        x_namespaces={
            namespace: Namespace(),
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(RuntimeError):
        # Correct event name but no namespace:
        server.emit(channel_name, faker.pydict(value_types=[str, int]))


def test_emit_event_that_has_no_subscribe_operation_raises_runtime_error(faker: Faker):
    namespace = f"/{faker.pystr()}"
    channel_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=channel_name, namespace=namespace): Channel(
                publish=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
        x_namespaces={
            namespace: Namespace(),
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(RuntimeError):
        server.emit(
            channel_name, faker.pydict(value_types=[str, int]), namespace=namespace
        )


def test_emit_event_with_invalid_args_fails_validation(faker: Faker):
    namespace = f"/{faker.pystr()}"
    channel_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=channel_name, namespace=namespace): Channel(
                subscribe=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
        x_namespaces={
            namespace: Namespace(),
        },
    )
    server = AsynctionSocketIO(spec)

    with pytest.raises(jsonschema.ValidationError):
        # Event args have invalid schema
        server.emit(channel_name, faker.pystr(), namespace=namespace)


@mock.patch.object(SocketIO, "emit")
def test_emit_valid_event_invokes_super_method(
    super_method_mock: mock.Mock, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    channel_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=channel_name, namespace=namespace): Channel(
                subscribe=Operation(
                    message=Message(payload={"type": "string"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
        x_namespaces={
            namespace: Namespace(),
        },
    )
    server = AsynctionSocketIO(spec)

    event_args = [faker.pystr()]
    server.emit(channel_name, *event_args, namespace=namespace)
    super_method_mock.assert_called_once_with(
        channel_name, *event_args, namespace=namespace
    )


@mock.patch.object(SocketIO, "emit")
def test_emit_validiation_is_ginored_if_validation_flag_is_false(
    super_method_mock: mock.Mock, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    channel_name = faker.pystr()
    spec = AsyncApiSpec(
        channels={
            ChannelPath(event_name=channel_name, namespace=namespace): Channel(
                subscribe=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
        x_namespaces={
            namespace: Namespace(),
        },
    )
    server = AsynctionSocketIO(spec, validation=False)

    event_args = [faker.pystr()]  # invalid args
    server.emit(channel_name, *event_args, namespace=namespace)

    # super method called because validation was skipped
    super_method_mock.assert_called_once_with(
        channel_name, *event_args, namespace=namespace
    )
