from unittest.mock import Mock

import pytest
import socketio
from socketio import exceptions as socketio_exceptions


@pytest.mark.filterwarnings("error")
def test_admin_namespace_with_correct_token(server_url: str, client: socketio.Client):
    server_metric_event = "server metric"

    mock_ack = Mock()

    @client.on(server_metric_event, namespace="/admin")
    def _server_metric(data):
        assert data["name"] == "CPU_COUNT"
        assert data["value"] > 0
        mock_ack(server_metric_event)

    client.connect(f"{server_url}?token=admin", namespaces=["/admin"])
    mock_ack.assert_called_once_with(server_metric_event)


@pytest.mark.filterwarnings("error")
def test_admin_namespace_with_faulty_token(server_url: str, client: socketio.Client):
    with pytest.raises(socketio_exceptions.ConnectionError):
        client.connect(f"{server_url}?token=not-admin", namespaces=["/admin"])
