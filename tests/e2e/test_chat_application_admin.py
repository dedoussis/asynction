from typing import Callable
from unittest.mock import Mock

import pytest
import socketio
from socketio import exceptions as socketio_exceptions


def test_admin_namespace_with_correct_token(
    server_url: str, socketio_client_factory: Callable[[], socketio.Client]
):
    admin_client = socketio_client_factory()

    server_metric_event = "server metric"

    mock_ack = Mock()

    @admin_client.on(server_metric_event, namespace="/admin")
    def _server_metric(data):
        assert data["name"] == "CPU_COUNT"
        assert data["value"] > 0
        mock_ack(server_metric_event)

    admin_client.connect(f"{server_url}?token=admin", namespaces=["/admin"], wait=True)
    admin_client.disconnect()
    mock_ack.assert_called_once_with(server_metric_event)


def test_admin_namespace_with_faulty_token(
    server_url: str, socketio_client_factory: Callable[[], socketio.Client]
):
    admin_client = socketio_client_factory()
    with pytest.raises(socketio_exceptions.ConnectionError):
        admin_client.connect(
            f"{server_url}?token=not-admin", namespaces=["/admin"], wait=True
        )
    admin_client.disconnect()
