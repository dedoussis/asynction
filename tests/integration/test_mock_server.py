from typing import Callable
from unittest.mock import patch

from flask import Flask
from flask_socketio import SocketIO

from asynction import MockAsynctionSocketIO
from asynction.types import GLOBAL_NAMESPACE
from tests.fixtures import FixturePaths

MockAsynctionFactory = Callable[..., MockAsynctionSocketIO]


def test_client_receives_messages_from_mock_server(
    mock_asynction_socketio_server_factory: MockAsynctionFactory,
    flask_app: Flask,
    fixture_paths: FixturePaths,
):
    mock_asio = mock_asynction_socketio_server_factory(spec_path=fixture_paths.echo)

    with patch.object(SocketIO, "run"):
        mock_asio.run(flask_app)

    flask_test_client = flask_app.test_client()
    socketio_test_client = mock_asio.test_client(
        flask_app, flask_test_client=flask_test_client
    )
    mock_asio.sleep(mock_asio.subscription_task_interval)
    received = socketio_test_client.get_received()

    assert len(received) > 0
    for event in received:
        assert event["name"] == "echo"
        assert event["namespace"] == GLOBAL_NAMESPACE
        echo_message = event["args"][0]
        assert isinstance(echo_message, str)
        assert " " in echo_message
        assert echo_message.endswith(".")
