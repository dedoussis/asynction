from enum import Enum
from time import sleep
from typing import Callable
from typing import Mapping

import pytest
import socketio
from faker import Faker

WAIT_INTERVAL = 0.2


class Event(Enum):
    USER_JOINED = "user joined"
    USER_LEFT = "user left"
    CONNECT = "connect"
    TYPING = "typing"
    STOP_TYPING = "stop typing"
    ADD_USER = "add user"
    NEW_MESSAGE = "new message"


@pytest.mark.filterwarnings("error")
def test_main_namespace(
    server_url: str,
    socketio_client_factory: Callable[[], socketio.Client],
    faker: Faker,
):
    users: Mapping[str, socketio.Client] = {
        faker.name(): socketio_client_factory()
        for _ in range(faker.pyint(min_value=3, max_value=6))
    }

    MESSAGE_TEMPLATE = "Hello, my name is {}"

    for username, client in users.items():

        @client.on(Event.CONNECT.value)
        def _connect():
            assert True

        @client.on(Event.USER_JOINED.value)
        def _user_joined(data, username: str = username):
            assert "numUsers" in data
            assert data["username"] in users
            assert data["username"] != username

        @client.on(Event.USER_LEFT.value)
        def _user_left(data):
            assert data["numUsers"] < len(users)

        @client.on(Event.TYPING.value)
        def _typing(data, username: str = username):
            assert data["username"] in users
            assert data["username"] != username

        @client.on(Event.STOP_TYPING.value)
        def _stop_typing(data, username: str = username):
            assert data["username"] in users
            assert data["username"] != username

        @client.on(Event.NEW_MESSAGE.value)
        def _new_message(data, username: str = username):
            assert data["username"] in users
            assert data["username"] != username
            assert data["message"] == MESSAGE_TEMPLATE.format(data["username"])

    for username, client in users.items():
        client.connect(server_url)
        client.emit(Event.ADD_USER.value, username)
        sleep(WAIT_INTERVAL)

    for username, client in users.items():
        client.emit(Event.TYPING.value)
        sleep(WAIT_INTERVAL)
        client.emit(Event.STOP_TYPING.value)
        sleep(WAIT_INTERVAL)
        client.emit(Event.NEW_MESSAGE.value, MESSAGE_TEMPLATE.format(username))

    for client in users.values():
        client.disconnect()
        sleep(WAIT_INTERVAL)


@pytest.mark.filterwarnings("error")
def test_admin_namespace(
    server_url: str,
    socketio_client_factory: Callable[[], socketio.Client],
    faker: Faker,
):
    assert False
