import os
from typing import Callable

import pytest
import socketio


@pytest.fixture
def server_url() -> str:
    return os.environ["SERVER_URL"]


@pytest.fixture
def socketio_client_factory() -> Callable[[], socketio.Client]:
    def factory():
        return socketio.Client()

    return factory
