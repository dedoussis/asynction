from pathlib import Path

import pytest
from faker import Faker

from asynction import AsynctionSocketIO
from asynction.exceptions import PayloadValidationException


def test_emit_valid_message_from_external_process_(
    message_queue_url: str,
    external_process_spec_path: Path,
    faker: Faker,
):
    external_process_server = AsynctionSocketIO.from_spec(
        spec_path=external_process_spec_path, message_queue=message_queue_url
    )

    external_process_server.emit(
        "new message", {"username": faker.pystr(), "message": faker.pystr()}
    )
    assert True


def test_emit_invalid_message_from_external_process_(
    message_queue_url: str,
    external_process_spec_path: Path,
    faker: Faker,
):
    external_process_server = AsynctionSocketIO.from_spec(
        spec_path=external_process_spec_path, message_queue=message_queue_url
    )

    with pytest.raises(PayloadValidationException):
        external_process_server.emit(
            "new message", {"username": faker.pystr(), "message": faker.pyint()}
        )
