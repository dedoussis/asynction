import base64
from enum import Enum
from typing import Callable

import pytest
import yaml
from faker import Faker
from flask import Flask
from flask_socketio import SocketIO

import asynction
from asynction.exceptions import BindingsValidationException
from asynction.exceptions import MessageAckValidationException
from asynction.exceptions import PayloadValidationException
from asynction.server import resolve_references
from tests.fixtures import FixturePaths

AsynctionFactory = Callable[..., SocketIO]


class FactoryFixture(Enum):
    ASYNCTION_SOCKET_IO = "asynction_socketio_server_factory"
    MOCK_ASYNCTION_SOCKET_IO = "mock_asynction_socketio_server_factory"


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_can_successfully_connect(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    socketio_server = server_factory()
    flask_test_client = flask_app.test_client()
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client
    )

    assert socketio_test_client.is_connected()


def test_client_emits_and_receives_message_successfully(
    asynction_socketio_server_factory: AsynctionFactory,
    flask_app: Flask,
    faker: Faker,
    fixture_paths: FixturePaths,
):
    socketio_server = asynction_socketio_server_factory(spec_path=fixture_paths.echo)
    flask_test_client = flask_app.test_client()
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client
    )
    socketio_test_client.get_received()

    message_to_echo = faker.pystr()
    socketio_test_client.emit("echo", message_to_echo)

    received = socketio_test_client.get_received()

    assert len(received) == 1
    received_args = received[0]["args"]
    assert len(received_args) == 1
    assert received_args[0] == message_to_echo


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_emitting_invalid_message(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    faker: Faker,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    socketio_server = server_factory(spec_path=fixture_paths.echo)
    flask_test_client = flask_app.test_client()
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client
    )
    socketio_test_client.get_received()
    with pytest.raises(PayloadValidationException):
        socketio_test_client.emit("echo", faker.pyint())


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_server_emitting_invalid_message(
    factory_fixture: FactoryFixture,
    fixture_paths: FixturePaths,
    faker: Faker,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    socketio_server = server_factory(spec_path=fixture_paths.echo)
    with pytest.raises(PayloadValidationException):
        socketio_server.emit("echo", faker.pyint())


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_connecting_with_valid_bindings(
    factory_fixture: FactoryFixture,
    fixture_paths: FixturePaths,
    flask_app: Flask,
    faker: Faker,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    socketio_server = server_factory(spec_path=fixture_paths.echo)
    flask_test_client = flask_app.test_client()

    restricted_namespace = "/admin"
    socketio_test_client = socketio_server.test_client(
        flask_app,
        namespace=restricted_namespace,
        query_string=f"?token={faker.pystr()}",
        flask_test_client=flask_test_client,
    )
    socketio_test_client.get_received(restricted_namespace)
    assert True


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_connecting_with_invalid_bindings(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    socketio_server = server_factory(spec_path=fixture_paths.echo)
    flask_test_client = flask_app.test_client()

    with pytest.raises(BindingsValidationException):
        socketio_server.test_client(
            flask_app,
            namespace="/admin",
            query_string="",
            flask_test_client=flask_test_client,
        )


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_can_connect_to_server_that_uses_server_name_and_render_docs(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    socketio_server = server_factory(
        spec_path=fixture_paths.simple_with_servers, server_name="production"
    )
    flask_test_client = flask_app.test_client()

    socketio_test_client = socketio_server.test_client(
        flask_app,
        flask_test_client=flask_test_client,
    )
    socketio_test_client.get_received()
    assert True

    resp = flask_test_client.get("/api/docs")

    assert resp.status_code == 200
    assert resp.mimetype == "text/html"
    assert "AsyncApiStandalone.hydrate" in resp.data.decode()


def test_client_emits_invalid_msg_and_server_emits_back_via_validation_error_handler(
    asynction_socketio_server_factory: AsynctionFactory,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    faker: Faker,
):
    socketio_server = asynction_socketio_server_factory(
        spec_path=fixture_paths.echo,
    )

    flask_test_client = flask_app.test_client()

    namespace_with_error_feedback = "/echo_with_error_feedback"

    socketio_test_client = socketio_server.test_client(
        flask_app,
        namespace=namespace_with_error_feedback,
        flask_test_client=flask_test_client,
    )

    socketio_test_client.get_received(namespace_with_error_feedback)

    message_to_echo = faker.pyint()
    socketio_test_client.emit(
        "echo", message_to_echo, namespace=namespace_with_error_feedback
    )
    received = socketio_test_client.get_received(namespace_with_error_feedback)
    assert len(received) == 1
    assert received[0]["name"] == "echo errors"


def test_client_emits_valid_msg_and_server_returns_invalid_ack(
    asynction_socketio_server_factory: AsynctionFactory,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    faker: Faker,
):
    socketio_server = asynction_socketio_server_factory(
        spec_path=fixture_paths.echo,
    )

    flask_test_client = flask_app.test_client()

    socketio_test_client = socketio_server.test_client(
        flask_app,
        flask_test_client=flask_test_client,
    )

    def cb(ack_data: bool):
        assert isinstance(ack_data, bool)

    with pytest.raises(MessageAckValidationException):
        socketio_test_client.emit("echo with invalid ack", faker.pystr(), callback=cb)


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_docs_rendered_html_endpoint(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    _ = server_factory(
        spec_path=fixture_paths.simple,
    )

    flask_test_client = flask_app.test_client()

    resp = flask_test_client.get("/docs")

    assert resp.status_code == 200
    assert resp.mimetype == "text/html"
    assert "AsyncApiStandalone.hydrate" in resp.data.decode()


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_docs_raw_specification_endpoint(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)
    _ = server_factory(
        spec_path=fixture_paths.simple,
    )

    flask_test_client = flask_app.test_client()

    resp = flask_test_client.get("/docs/asyncapi.json")

    with fixture_paths.simple.open() as f:
        assert resolve_references(yaml.safe_load(f.read())) == resp.json


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_fails_to_connect_with_no_auth(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)

    socketio_server = server_factory(
        spec_path=fixture_paths.security, server_name="test"
    )
    flask_test_client = flask_app.test_client()

    with pytest.raises(ConnectionRefusedError):
        socketio_test_client = socketio_server.test_client(
            flask_app, flask_test_client=flask_test_client
        )

        assert socketio_test_client.is_connected() is False


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_connects_with_http_basic_auth(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)

    socketio_server = server_factory(
        spec_path=fixture_paths.security, server_name="test"
    )
    flask_test_client = flask_app.test_client()

    basic_auth = base64.b64encode("username:password".encode()).decode()
    headers = {"Authorization": f"basic {basic_auth}"}
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client, headers=headers
    )

    assert socketio_test_client.is_connected() is True


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_connects_with_http_bearer_auth(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)

    socketio_server = server_factory(
        spec_path=fixture_paths.security, server_name="test"
    )
    flask_test_client = flask_app.test_client()

    basic_auth = base64.b64encode("username:password".encode()).decode()
    headers = {"Authorization": f"bearer {basic_auth}"}
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client, headers=headers
    )

    assert socketio_test_client.is_connected() is True


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_connects_with_http_api_key_auth(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)

    socketio_server = server_factory(
        spec_path=fixture_paths.security, server_name="test"
    )
    flask_test_client = flask_app.test_client()

    basic_auth = base64.b64encode("username:password".encode()).decode()
    query = f"api_key={basic_auth}"
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client, query_string=query
    )

    assert socketio_test_client.is_connected() is True


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_connects_with_oauth2(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)

    socketio_server = server_factory(
        spec_path=fixture_paths.security_oauth2, server_name="test"
    )
    flask_test_client = flask_app.test_client()

    basic_auth = base64.b64encode("username:password".encode()).decode()
    headers = {"Authorization": f"bearer {basic_auth}"}
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client, headers=headers
    )

    assert socketio_test_client.is_connected() is True


@pytest.mark.parametrize(
    argnames="factory_fixture",
    argvalues=[
        FactoryFixture.ASYNCTION_SOCKET_IO,
        FactoryFixture.MOCK_ASYNCTION_SOCKET_IO,
    ],
    ids=["server", "mock_server"],
)
def test_client_connects_with_namespace_security(
    factory_fixture: FactoryFixture,
    flask_app: Flask,
    fixture_paths: FixturePaths,
    request: pytest.FixtureRequest,
):
    server_factory: AsynctionFactory = request.getfixturevalue(factory_fixture.value)

    socketio_server = server_factory(
        spec_path=fixture_paths.namespace_security, server_name="test"
    )
    flask_test_client = flask_app.test_client()

    # connect to default namespace which is secured with basic auth
    basic_auth = base64.b64encode("username:password".encode()).decode()
    headers = {"Authorization": f"basic {basic_auth}"}
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client, headers=headers
    )

    assert socketio_test_client.is_connected() is True

    socketio_test_client.disconnect()

    secure_namespace = "/bearer_secured"

    # now try to use basic auth on the bearer_secured namespace
    # this should fail because the namespace security should have
    # overwritten the server security scheme
    with pytest.raises(asynction.SecurityException):
        socketio_server.test_client(
            flask_app,
            namespace=secure_namespace,
            flask_test_client=flask_test_client,
            headers=headers,
        )

    # now try to connect to the bearer_secured namespace with bearer auth
    headers = {"Authorization": f"bearer {basic_auth}"}
    socketio_test_client = socketio_server.test_client(
        flask_app,
        namespace=secure_namespace,
        flask_test_client=flask_test_client,
        headers=headers,
    )

    assert socketio_test_client.is_connected(secure_namespace) is True
