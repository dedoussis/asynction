from pathlib import Path
from typing import Callable
from typing import Optional

import pytest
from flask import Flask
from flask_socketio import SocketIO

from asynction import AsynctionSocketIO
from asynction import MockAsynctionSocketIO
from tests.fixtures import FixturePaths


@pytest.fixture
def flask_app() -> Flask:
    return Flask(__name__)


@pytest.fixture
def asynction_socketio_server_factory(
    fixture_paths: FixturePaths, flask_app: Flask
) -> Callable[[Path], SocketIO]:
    def factory(
        spec_path: Path = fixture_paths.simple, server_name: Optional[str] = None
    ) -> SocketIO:
        return AsynctionSocketIO.from_spec(
            spec_path=spec_path, server_name=server_name, app=flask_app
        )

    return factory


@pytest.fixture
def mock_asynction_socketio_server_factory(
    fixture_paths: FixturePaths, flask_app: Flask
) -> Callable[[Path], SocketIO]:
    def factory(
        spec_path: Path = fixture_paths.simple, server_name: Optional[str] = None
    ) -> SocketIO:
        return MockAsynctionSocketIO.from_spec(
            spec_path=spec_path, server_name=server_name, app=flask_app
        )

    return factory
