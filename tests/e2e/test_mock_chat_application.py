from unittest.mock import Mock

import jsonschema
import pytest
import socketio


@pytest.mark.parametrize(
    argnames="server_url_fixture",
    argvalues=["mock_server_url", "cli_mock_server_url"],
    ids=["mock_server", "cli_mock_server"],
)
@pytest.mark.filterwarnings("error")
def test_automatic_mock_event_emission(
    server_url_fixture: str,
    mock_server_wait_interval: float,
    client: socketio.Client,
    request: pytest.FixtureRequest,
):
    server_url: str = request.getfixturevalue(server_url_fixture)
    new_message_event = "new message"
    new_message_mock_ack = Mock()

    @client.on(new_message_event)
    def _new_message_handler(data):
        jsonschema.validate(
            data, {"username": {"type": "string"}, "message": {"type": "string"}}
        )

        # Assert that message is of sentence format:
        assert data["message"].endswith(".")
        assert " " in data["message"]

        # Assert that username is a first name:
        assert data["username"].istitle()

        new_message_mock_ack(new_message_event)

    typing_event = "typing"
    typing_mock_ack = Mock()

    @client.on(typing_event)
    def _typing_handler(data):
        jsonschema.validate(data, {"username": {"type": "string"}})

        # Assert that username is a first name:
        assert data["username"].istitle()
        typing_mock_ack(typing_event)

    user_joined_event = "user joined"
    user_joined_mock_ack = Mock()

    @client.on(user_joined_event)
    def _user_joined_handler(data):
        jsonschema.validate(
            data, {"username": {"type": "string"}, "numUsers": {"type": "integer"}}
        )

        # Assert that username is a first name:
        assert data["username"].istitle()
        user_joined_mock_ack(user_joined_event)

    client.connect(server_url, wait=False)
    # Make sure that all events have been emitted:
    client.sleep(mock_server_wait_interval)

    new_message_mock_ack.assert_called_with(new_message_event)
    typing_mock_ack.assert_called_with(typing_event)
    user_joined_mock_ack.assert_called_with(user_joined_event)
