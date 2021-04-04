from typing import Callable
from unittest.mock import Mock
from unittest.mock import patch

from flask.app import Flask
from flask_socketio import SocketIO

from tests.fixtures import handlers

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


@patch.object(handlers, "my_handler")
def test_client_emitting_message_invokes_handler(
    mock_handler: Mock,
    asynction_socketio_server_factory: AsynctionFactory,
    flask_app: Flask,
):
    socketio_server = asynction_socketio_server_factory()
    flask_test_client = flask_app.test_client()
    socketio_test_client = socketio_server.test_client(
        flask_app, flask_test_client=flask_test_client
    )
    socketio_test_client.emit("signedup")
    mock_handler.assert_called_once()
