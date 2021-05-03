from typing import Any

from flask import request
from flask_socketio import emit


def ping(message: Any) -> None:
    # Dummy handler
    pass


def connect() -> None:
    # Dummy handler
    pass


def disconnect() -> None:
    # Dummy handler
    pass


def some_error() -> None:
    # Dummy handler
    pass


def echo(message: str) -> None:
    emit("echo", message)


def authenticated_connect() -> None:
    assert request.args.get("token")
