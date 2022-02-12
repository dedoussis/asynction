from pathlib import Path
from typing import Any
from typing import Optional
from typing import Union

import pytest
from flask import Flask
from flask_socketio import SocketIO

from asynction import AsynctionSocketIO
from asynction import MockAsynctionSocketIO
from asynction.types import JSONMapping
from tests.fixtures import FixturePaths
from tests.utils import AsynctionFactory


@pytest.fixture
def flask_app() -> Flask:
    return Flask(__name__)


@pytest.fixture
def asynction_socketio_server_factory(
    fixture_paths: FixturePaths, flask_app: Flask
) -> AsynctionFactory:
    def factory(
        *args: Any,
        app: Optional[Flask] = flask_app,
        spec_path: Union[Path, JSONMapping] = fixture_paths.simple,
        **kwargs: Any
    ) -> SocketIO:
        return AsynctionSocketIO.from_spec(
            spec_path=spec_path,
            app=app,
            **kwargs,
        )

    return factory


@pytest.fixture
def mock_asynction_socketio_server_factory(
    fixture_paths: FixturePaths, flask_app: Flask
) -> AsynctionFactory:
    def factory(
        *args: Any,
        app: Optional[Flask] = flask_app,
        spec_path: Union[Path, JSONMapping] = fixture_paths.simple,
        **kwargs: Any
    ) -> SocketIO:
        return MockAsynctionSocketIO.from_spec(
            spec_path=spec_path,
            app=app,
            async_mode="threading",
            **kwargs,
        )

    return factory
