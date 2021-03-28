from typing import Optional

import pytest
from faker import Faker
from flask_socketio import SocketIO

from asynction import DEFAULT_NAMESPACES
from asynction import MAIN_NAMESPACE
from asynction import AsyncApiSpec
from asynction import AsynctionSocketIO
from asynction import Channel
from asynction import Message
from asynction import Namespace
from asynction import Operation
from asynction import decompose_channel_path
from asynction import load_handler
from asynction import load_spec
from asynction import register_error_handlers
from asynction import register_event_handlers
from asynction import resolve_references
from tests.fixtures import FixturePaths
from tests.fixtures.handlers import my_handler
from tests.fixtures.handlers import my_other_handler


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


def test_channel_raises_value_error_if_operation_id_is_not_defined_in_subscribe_operation(
    faker: Faker,
):
    with pytest.raises(ValueError):
        Channel(subscribe=Operation(Message(payload=faker.pydict())))


def test_resolve_references_resolves_successfully():
    raw_spec = {
        "channels": {
            "user/signedup": {
                "subscribe": {"message": {"$ref": "#/components/messages/UserSignedUp"}}
            }
        },
        "components": {"messages": {"UserSignedUp": {"type": "object"}}},
    }

    resolved = {
        "channels": {
            "user/signedup": {
                "subscribe": {
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
        ("foo", "foo", None),
        ("foo/bar/baz", "baz", "/foo/bar"),
        ("/foo/bar", "bar", "/foo"),
    ],
    ids=[
        "path_with_namespace",
        "path_without_namespace",
        "path_with_nested_namespace",
        "path_with_leading_separator",
    ],
)
def test_decompose_channel_path(
    channel_path: str, expected_name: str, expected_namespace: Optional[str]
):
    assert decompose_channel_path(channel_path) == (expected_name, expected_namespace)


def test_load_handler():
    handler_id = "tests.fixtures.handlers.my_handler"
    assert load_handler(handler_id) == my_handler


def test_register_event_handlers_without_namespace_uses_main(
    faker: Faker,
):
    channel_name = faker.pystr()
    server = SocketIO()
    spec = AsyncApiSpec(
        channels={
            channel_name: Channel(
                subscribe=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                )
            )
        }
    )

    register_event_handlers(server=server, spec=spec)
    assert len(server.handlers) == 1
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == channel_name
    assert registered_handler.__wrapped__ == my_handler
    assert registered_namespace == MAIN_NAMESPACE


def test_register_event_handlers_with_namespace(
    faker: Faker,
):
    namespace = f"{faker.pystr()}"
    channel_name = faker.pystr()
    server = SocketIO()
    spec = AsyncApiSpec(
        channels={
            f"{namespace}/{channel_name}": Channel(
                subscribe=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
        x_namespaces={
            f"/{namespace}": Namespace(),
        },
    )

    register_event_handlers(server=server, spec=spec)
    assert len(server.handlers) == 1
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == channel_name
    assert registered_handler.__wrapped__ == my_handler
    assert registered_namespace == f"/{namespace}"


def test_register_event_handlers_raises_value_error_if_namespace_not_defined_in_definitions(
    faker: Faker,
):
    server = SocketIO()
    spec = AsyncApiSpec(
        channels={
            f"{faker.pystr()}/{faker.pystr()}": Channel(
                subscribe=Operation(
                    message=Message(payload={"type": "object"}),
                    operationId="tests.fixtures.handlers.my_handler",
                ),
            )
        },
    )

    with pytest.raises(ValueError):
        register_event_handlers(server=server, spec=spec)


def test_register_error_handlers_for_each_namespace(faker: Faker):
    server = SocketIO()
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

    register_error_handlers(server=server, spec=spec)
    assert server.default_exception_handler == my_handler
    assert server.exception_handlers[custom_namespace] == my_other_handler
