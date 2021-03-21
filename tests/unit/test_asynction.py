from typing import Optional

import pytest

from asynction import AsynctionSocketIO
from asynction import decompose_channel_path
from asynction import load_operation_handler
from asynction import resolve_references
from tests.fixtures import FixturePaths
from tests.fixtures.handlers import user_signedup


def test_asynction_socketio_from_spec(fixture_paths: FixturePaths):
    asio = AsynctionSocketIO.from_spec(spec_path=fixture_paths.simple)
    assert isinstance(asio, AsynctionSocketIO)


def test_resolve_references_resolves_successfully():
    raw_spec = {
        "channels": {
            "user/signedup": {
                "subscribe": {"message": {"$ref": "#/components/messages/UserSignedUp"}}
            }
        },
        "components": {"messages": {"UserSignedUp": {"type": "object"}}},
    }

    resolved = {
        "channels": {
            "user/signedup": {
                "subscribe": {
                    "message": {
                        "type": "object",
                    }
                }
            }
        },
        "components": {"messages": {"UserSignedUp": {"type": "object"}}},
    }

    assert resolve_references(raw_spec) == resolved


@pytest.mark.parametrize(
    argnames=("channel_path", "expected_name", "expected_namespace"),
    argvalues=[
        ("foo/bar", "bar", "/foo"),
        ("foo", "foo", None),
        ("foo/bar/baz", "baz", "/foo/bar"),
        ("/foo/bar", "bar", "/foo"),
    ],
    ids=[
        "path_with_namespace",
        "path_without_namespace",
        "path_with_nested_namespace",
        "path_with_leading_separator",
    ],
)
def test_decompose_channel_path(
    channel_path: str, expected_name: str, expected_namespace: Optional[str]
):
    assert decompose_channel_path(channel_path) == (expected_name, expected_namespace)


def test_load_operation_handler():
    operation_id = "tests.fixtures.handlers.user_signedup"
    assert load_operation_handler(operation_id) == user_signedup
