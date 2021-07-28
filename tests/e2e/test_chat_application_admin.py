from typing import Callable

import pytest
import socketio
from socketio import exceptions as socketio_exceptions


def test_admin_namespace_with_correct_token(
    server_url: str, socketio_client_factory: Callable[[], socketio.Client]
):
    admin_client = socketio_client_factory()
    admin_client.connect(f"{server_url}?token=admin", namespaces=["/admin"], wait=True)
    assert True
    admin_client.disconnect()


def test_admin_namespace_with_faulty_token(
    server_url: str, socketio_client_factory: Callable[[], socketio.Client]
):
    admin_client = socketio_client_factory()
    with pytest.raises(socketio_exceptions.ConnectionError):
        admin_client.connect(
            f"{server_url}?token=not-admin", namespaces=["/admin"], wait=True
        )
    admin_client.disconnect()
