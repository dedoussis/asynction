from typing import Optional

import pytest
from faker import Faker
from svarog import forge

from asynction.types import MAIN_NAMESPACE
from asynction.types import Channel
from asynction.types import ChannelPath
from asynction.types import Message
from asynction.types import Operation


def test_channel_raises_value_error_if_operation_id_is_not_defined_in_sub_operation(
    faker: Faker,
):
    with pytest.raises(ValueError):
        Channel(publish=Operation(Message(payload=faker.pydict())))


@pytest.mark.parametrize(
    argnames=("channel_path", "expected_name", "expected_namespace"),
    argvalues=[
        ("foo/bar", "bar", "/foo"),
        ("foo", "foo", MAIN_NAMESPACE),
        ("/foo", "foo", MAIN_NAMESPACE),
        ("foo/bar/baz", "baz", "/foo/bar"),
        ("/foo/bar", "bar", "/foo"),
    ],
    ids=[
        "path_with_namespace",
        "path_without_namespace",
        "path_without_namespace_and_leading_separator",
        "path_with_nested_namespace",
        "path_with_leading_separator",
    ],
)
def test_channel_path_deserialization(
    channel_path: str, expected_name: str, expected_namespace: Optional[str]
):
    cp = forge(ChannelPath, channel_path)
    assert cp.event_name == expected_name
    assert cp.namespace == expected_namespace
