from typing import Callable

import jsonschema
import pytest
from faker import Faker
from flask.app import Flask
from flask_socketio import SocketIO

from tests.fixtures import FixturePaths

AsynctionFactory = Callable[..., SocketIO]


def test_client_can_successfully_connect(
    asynction_socketio_server_factory: AsynctionFactory, flask_app: Flask
):
    socketio_server = asynction_socketio_server_factory()
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
    assert len(received[0]["args"]) == 1
    assert received[0]["args"][0] == message_to_echo


def test_client_emitting_invalid_message(
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
    with pytest.raises(jsonschema.ValidationError):
        socketio_test_client.emit("echo", faker.pyint())


def test_server_emitting_invalid_message(
    asynction_socketio_server_factory: AsynctionFactory,
    fixture_paths: FixturePaths,
    faker: Faker,
):
    socketio_server = asynction_socketio_server_factory(spec_path=fixture_paths.echo)
    with pytest.raises(jsonschema.ValidationError):
        socketio_server.emit("echo", faker.pyint())


def test_client_connecting_with_valid_bindings(
    asynction_socketio_server_factory: AsynctionFactory,
    flask_app: Flask,
    faker: Faker,
    fixture_paths: FixturePaths,
):
    socketio_server = asynction_socketio_server_factory(spec_path=fixture_paths.echo)
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


def test_client_connecting_with_invalid_bindings(
    asynction_socketio_server_factory: AsynctionFactory,
    flask_app: Flask,
    fixture_paths: FixturePaths,
):
    socketio_server = asynction_socketio_server_factory(spec_path=fixture_paths.echo)
    flask_test_client = flask_app.test_client()

    with pytest.raises(jsonschema.ValidationError):
        socketio_server.test_client(
            flask_app,
            namespace="/admin",
            query_string="",
            flask_test_client=flask_test_client,
        )


def test_client_can_connect_to_server_that_uses_server_name(
    asynction_socketio_server_factory: AsynctionFactory,
    flask_app: Flask,
    fixture_paths: FixturePaths,
):
    socketio_server = asynction_socketio_server_factory(
        spec_path=fixture_paths.simple_with_servers, server_name="production"
    )
    flask_test_client = flask_app.test_client()

    socketio_test_client = socketio_server.test_client(
        flask_app,
        flask_test_client=flask_test_client,
    )
    socketio_test_client.get_received()
    assert True
