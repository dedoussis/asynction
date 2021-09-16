import os
from typing import Callable

import pytest
import socketio


@pytest.fixture
def server_url() -> str:
    return os.environ["SERVER_URL"]


@pytest.fixture
def mock_server_url() -> str:
    return os.environ["MOCK_SERVER_URL"]


@pytest.fixture
def cli_mock_server_url() -> str:
    return os.environ["MOCK_SERVER_URL"]


@pytest.fixture
def mock_client_wait_timeout() -> float:
    return float(os.environ["MOCK_CLIENT_WAIT_TIMEOUT"])


@pytest.fixture
def mock_client_wait_interval() -> float:
    return float(os.environ["MOCK_CLIENT_WAIT_INTERVAL"])


@pytest.fixture
def socketio_client_factory() -> Callable[[], socketio.Client]:
    def factory():
        return socketio.Client(logger=True, engineio_logger=True)

    return factory


@pytest.fixture
def client(socketio_client_factory: Callable[[], socketio.Client]) -> socketio.Client:
    client = socketio_client_factory()
    yield client
    client.disconnect()
