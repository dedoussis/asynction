from typing import Optional

import pytest
from faker import Faker
from svarog import forge

from asynction import DEFAULT_NAMESPACES
from asynction import MAIN_NAMESPACE
from asynction import AsyncApiSpec
from asynction import AsynctionSocketIO
from asynction import Channel
from asynction import ChannelPath
from asynction import Message
from asynction import Namespace
from asynction import Operation
from asynction import load_handler
from asynction import load_spec
from asynction import resolve_references
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


def test_channel_raises_value_error_if_operation_id_is_not_defined_in_sub_operation(
    faker: Faker,
):
    with pytest.raises(ValueError):
        Channel(publish=Operation(Message(payload=faker.pydict())))


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


@pytest.mark.parametrize(
    argnames=("channel_path", "expected_name", "expected_namespace"),
    argvalues=[
        ("foo/bar", "bar", "/foo"),
        ("foo", "foo", MAIN_NAMESPACE),
        ("/foo", "foo", MAIN_NAMESPACE),
        ("foo/bar/baz", "baz", "/foo/bar"),
        ("/foo/bar", "bar", "/foo"),
    ],
    ids=[
        "path_with_namespace",
        "path_without_namespace",
        "path_without_namespace_and_leading_separator",
        "path_with_nested_namespace",
        "path_with_leading_separator",
    ],
)
def test_channel_path_deserialization(
    channel_path: str, expected_name: str, expected_namespace: Optional[str]
):
    cp = forge(ChannelPath, channel_path)
    assert cp.event_name == expected_name
    assert cp.namespace == expected_namespace


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
