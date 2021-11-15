import base64
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence

from flask import request
from flask_socketio import emit
from typing_extensions import TypedDict

from asynction.exceptions import ValidationException


def ping(message: Any) -> None:
    # Dummy handler
    pass


class PingAck(TypedDict):
    ack: bool


def ping_with_ack(message: Any) -> PingAck:
    return PingAck(ack=True)


def connect() -> None:
    # Dummy handler
    pass


def disconnect() -> None:
    # Dummy handler
    pass


def some_error() -> None:
    # Dummy handler
    pass


def echo(message: str) -> bool:
    emit("echo", message)
    return True


def echo_with_invalid_ack(message: str) -> int:
    emit("echo", message)
    return 23


def authenticated_connect() -> None:
    assert request.args.get("token")


def echo_failed_validation(e: Exception) -> None:
    if isinstance(e, ValidationException):
        emit("echo errors", "Incoming message failed validation")


def basic_info(
    username: str, password: str, required_scopes: Optional[Sequence[str]] = None
) -> Mapping:
    if username != "username" or password != "password":
        raise ConnectionRefusedError("Invalid username or password")

    scopes = list(required_scopes) if required_scopes else []
    return dict(user=username, scopes=scopes)


def bearer_info(
    token: str,
    required_scopes: Optional[Sequence[str]] = None,
    bearer_format: Optional[str] = None,
) -> Mapping:
    username, password = base64.b64decode(token).decode().split(":")
    if username != "username" or password != "password" or bearer_format != "test":
        raise ConnectionRefusedError("Invalid username or password")

    scopes = list(required_scopes) if required_scopes else []
    return dict(user=username, scopes=scopes)


def api_key_info(
    token: str,
    required_scopes: Optional[Sequence[str]] = None,
    bearer_format: Optional[str] = None,
) -> Mapping:
    username, password = base64.b64decode(token).decode().split(":")
    if username != "username" or password != "password":
        raise ConnectionRefusedError("Invalid username or password")

    scopes = list(required_scopes) if required_scopes else []
    print(scopes, required_scopes)
    return dict(user=username, scopes=scopes)


def token_info(token: str) -> Mapping:
    username, password = base64.b64decode(token).decode().split(":")
    if username != "username" or password != "password":
        raise ConnectionRefusedError("Invalid username or password")

    return dict(user=username, scopes=["a", "b"])
