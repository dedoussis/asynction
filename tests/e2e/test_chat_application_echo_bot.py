from enum import Enum
from typing import Callable
from typing import Iterator
from typing import Sequence
from typing import Tuple
from unittest.mock import Mock
from unittest.mock import call

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


Username = str
ApplicationClient = Tuple[Username, socketio.Client, Mock]

ECHO_MESSAGE_TEMPLATE = "{}'s echo: {}"
ECHO_MESSAGE_PREFIX = "echo "


@pytest.fixture
def echo_bot_username() -> Username:
    return "Echo Bot"


@pytest.fixture
def echo_bot(
    echo_bot_username: Username, socketio_client_factory: Callable[[], socketio.Client]
) -> Iterator[ApplicationClient]:
    echo_bot_client = socketio_client_factory()

    mock_ack = Mock()

    @echo_bot_client.on(Event.CONNECT.value)
    def _connect():
        assert True

    @echo_bot_client.on(Event.NEW_MESSAGE.value)
    def _new_message(data):
        if data["message"].startswith(ECHO_MESSAGE_PREFIX):
            echo_bot_client.emit(
                Event.NEW_MESSAGE.value,
                ECHO_MESSAGE_TEMPLATE.format(
                    data["username"], data["message"][len(ECHO_MESSAGE_PREFIX) :]
                ),
            )
            mock_ack(Event.NEW_MESSAGE)

    yield echo_bot_username, echo_bot_client, mock_ack
    echo_bot_client.disconnect()


@pytest.fixture
def echo_user_factory(
    echo_bot_username: Username,
    socketio_client_factory: Callable[[], socketio.Client],
    faker: Faker,
) -> Callable[[], ApplicationClient]:
    def factory() -> ApplicationClient:
        echo_user_username = faker.name()
        echo_user_message = faker.sentence()
        echo_user_client = socketio_client_factory()
        echo_user_client.message = echo_user_message

        mock_ack = Mock()

        @echo_user_client.on(Event.CONNECT.value)
        def _connect():
            assert True

        @echo_user_client.on(Event.NEW_MESSAGE.value)
        def _new_message(data):
            if data["username"] == echo_bot_username and data["message"].startswith(
                echo_user_username
            ):
                assert data["message"] == ECHO_MESSAGE_TEMPLATE.format(
                    echo_user_username, echo_user_message
                )
                mock_ack(Event.NEW_MESSAGE)

        return echo_user_username, echo_user_client, mock_ack

    return factory


@pytest.fixture
def echo_users(
    echo_user_factory: Callable[[], ApplicationClient],
    faker: Faker,
) -> Iterator[Sequence[ApplicationClient]]:
    echo_users: Sequence[ApplicationClient] = [
        echo_user_factory() for _ in range(faker.pyint(min_value=3, max_value=6))
    ]

    yield echo_users
    for _, client, _ in echo_users:
        client.disconnect()


@pytest.mark.filterwarnings("error")
def test_echo_bot(
    server_url: str,
    echo_bot: ApplicationClient,
    echo_users: Sequence[ApplicationClient],
):
    echo_bot_username, echo_bot_client, echo_bot_mock_ack = echo_bot
    echo_bot_client.connect(server_url)
    cb_mock = Mock()
    echo_bot_client.emit(Event.ADD_USER.value, echo_bot_username, callback=cb_mock)
    echo_bot_client.sleep(WAIT_INTERVAL)
    cb_mock.assert_called_once_with({"error": None})

    for echo_user_username, echo_user_client, echo_user_mock_ack in echo_users:
        echo_user_client.connect(server_url)
        cb_mock = Mock()
        echo_user_client.emit(
            Event.ADD_USER.value, echo_user_username, callback=cb_mock
        )
        echo_user_client.sleep(WAIT_INTERVAL)
        cb_mock.assert_called_once_with({"error": None})

    for echo_user_username, echo_user_client, echo_user_mock_ack in echo_users:
        echo_user_client.emit(Event.TYPING.value)
        echo_user_client.sleep(WAIT_INTERVAL)
        echo_user_client.emit(Event.STOP_TYPING.value)
        echo_user_client.sleep(WAIT_INTERVAL)
        echo_user_client.emit(
            Event.NEW_MESSAGE.value, ECHO_MESSAGE_PREFIX + echo_user_client.message
        )
        echo_user_client.sleep(WAIT_INTERVAL)
        echo_user_mock_ack.assert_has_calls([call(Event.NEW_MESSAGE)])

    echo_bot_mock_ack.assert_has_calls([call(Event.NEW_MESSAGE)] * len(echo_users))
