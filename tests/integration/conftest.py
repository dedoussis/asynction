from pathlib import Path
from typing import Callable

import pytest
from flask import Flask
from flask_socketio import SocketIO

from asynction import AsynctionSocketIO
from tests.fixtures import FixturePaths


@pytest.fixture
def flask_app() -> Flask:
    return Flask(__name__)


@pytest.fixture
def asynction_socketio_server_factory(
    fixture_paths: FixturePaths, flask_app: Flask
) -> Callable[[Path], SocketIO]:
    def factory(spec_path: Path = fixture_paths.simple) -> SocketIO:
        return AsynctionSocketIO.from_spec(spec_path=spec_path, app=flask_app)

    return factory
