#!/usr/bin/env python3
from gevent import monkey

monkey.patch_all()

import os
from pathlib import Path
from typing import MutableMapping
from typing import Optional

from flask import Flask
from flask import Request
from flask import request
from flask_socketio import emit
from typing_extensions import TypedDict

from asynction import AsynctionSocketIO

Sid = str
Username = str
username_store: MutableMapping[Sid, Username] = {}


def get_sid(request: Request) -> Sid:
    return request.sid  # type: ignore


def new_message(message: str) -> None:
    sid = get_sid(request)
    username = username_store[sid]
    emit(
        "new message",
        {"username": username, "message": message},
        broadcast=True,
        skip_sid=sid,
    )


def message_typing() -> None:
    sid = get_sid(request)
    username = username_store[sid]
    emit("typing", {"username": username}, broadcast=True, skip_sid=sid)


def stop_typing() -> None:
    sid = get_sid(request)
    username = username_store[sid]
    emit("stop typing", {"username": username}, broadcast=True, skip_sid=sid)


class AddUserAck(TypedDict):
    error: Optional[str]


def add_user(username: str) -> AddUserAck:
    if username in username_store.values():
        return AddUserAck(error=f"Username {username} already exists")

    sid = get_sid(request)
    username_store[sid] = username
    num_users = len(username_store)
    emit("login", {"numUsers": num_users})
    emit(
        "user joined",
        {"username": username, "numUsers": num_users},
        broadcast=True,
        skip_sid=sid,
    )
    return AddUserAck(error=None)


def disconnect() -> None:
    sid = get_sid(request)
    username = username_store.pop(sid, None)
    if username is not None:
        emit(
            "user left",
            {"username": username, "numUsers": len(username_store)},
            broadcast=True,
            skip_sid=sid,
        )


def admin_connect() -> None:
    token = request.args.get("token")
    if token != "admin":
        raise ConnectionRefusedError("Unauthorized!")

    emit("server metric", {"name": "CPU_COUNT", "value": os.cpu_count()})


flask_app = Flask(__name__)

asio = AsynctionSocketIO.from_spec(
    spec_path=Path(__file__).parent.joinpath("asyncapi.yml"),
    server_name=os.environ.get("ASYNCAPI_SERVER_NAME", "demo"),
    logger=True,
    async_mode="gevent",
    app=flask_app,
    cors_allowed_origins="*",
)

if __name__ == "__main__":
    asio.run(app=flask_app, debug=True, log_output=True, host="0.0.0.0")
