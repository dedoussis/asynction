import pytest
from faker import Faker
from svarog import forge

from asynction.types import GLOBAL_NAMESPACE
from asynction.types import AsyncApiSpec
from asynction.types import Channel
from asynction.types import ChannelBindings
from asynction.types import ChannelHandlers
from asynction.types import Message
from asynction.types import OneOfMessages
from asynction.types import Operation


def test_message_deserialisation(faker: Faker):
    name = faker.pystr()
    payload = faker.pydict(value_types=[str, int])
    x_handler = faker.pystr()
    message = forge(Message, {"name": name, "payload": payload, "x-handler": x_handler})

    assert message.name == name
    assert message.payload == payload
    assert message.x_handler == x_handler


def test_one_of_messages_deserialisation_of_one_of_structure(faker: Faker):
    n = faker.pyint(min_value=2, max_value=10)
    data = {
        "oneOf": [
            {
                "name": faker.pystr(),
                "payload": faker.pydict(value_types=[str, int]),
                "x-handler": faker.pystr(),
            }
            for _ in range(n)
        ]
    }

    one_of_messages = forge(OneOfMessages, data)
    assert len(one_of_messages.oneOf) == n


def test_one_of_messages_deserialisation_of_message_structure(faker: Faker):
    name = faker.pystr()
    payload = faker.pydict(value_types=[str, int])
    x_handler = faker.pystr()
    data = {"name": name, "payload": payload, "x-handler": x_handler}

    one_of_messages = forge(OneOfMessages, data)
    assert len(one_of_messages.oneOf) == 1
    assert one_of_messages.oneOf[0].name == name
    assert one_of_messages.oneOf[0].payload == payload
    assert one_of_messages.oneOf[0].x_handler == x_handler


def test_channel_deserialization(faker: Faker):
    data = {
        "subscribe": {
            "message": {
                "oneOf": [
                    {
                        "name": faker.pystr(),
                        "payload": faker.pydict(value_types=[str, int]),
                    }
                    for _ in range(faker.pyint(min_value=2, max_value=10))
                ]
            }
        },
        "publish": {
            "message": {
                "oneOf": [
                    {
                        "name": faker.pystr(),
                        "payload": faker.pydict(value_types=[str, int]),
                        "x-handler": faker.pydict(value_types=[str, int]),
                    }
                    for _ in range(faker.pyint(min_value=2, max_value=10))
                ]
            }
        },
        "bindings": {
            "ws": {
                "method": faker.pystr(),
                "query": faker.pydict(value_types=[str, int]),
            }
        },
        "x-handlers": {
            "connect": faker.pystr(),
            "disconnect": faker.pystr(),
        },
    }

    channel = forge(Channel, data)
    assert isinstance(channel.publish, Operation)
    assert isinstance(channel.subscribe, Operation)
    assert isinstance(channel.bindings, ChannelBindings)
    assert isinstance(channel.x_handlers, ChannelHandlers)


def test_channel_raises_value_error_if_publish_messages_miss_handler(faker: Faker):
    with pytest.raises(ValueError):
        Channel(
            subscribe=Operation(
                message=OneOfMessages(
                    oneOf=[
                        Message(
                            name=faker.pystr(),
                            payload=faker.pydict(value_types=[str, int]),
                        )
                    ]
                )
            ),
            publish=Operation(
                message=OneOfMessages(
                    oneOf=[
                        *[
                            Message(
                                name=faker.pystr(),
                                payload=faker.pydict(value_types=[str, int]),
                                x_handler=faker.pystr(),
                            )
                            for _ in range(faker.pyint(min_value=2, max_value=10))
                        ],
                        Message(
                            name=faker.pystr(),
                            payload=faker.pydict(value_types=[str, int]),
                        ),
                    ]
                )
            ),
        )


def test_async_api_spec_from_dict_allows_extra_attrs(faker: Faker):
    data = {
        "channels": {
            GLOBAL_NAMESPACE: {
                "description": faker.pystr(),
                "subscribe": {
                    "message": {
                        "oneOf": [
                            {
                                "name": faker.pystr(),
                                "summary": faker.sentence(),
                                "payload": faker.pydict(value_types=[str, int]),
                            }
                            for _ in range(faker.pyint(min_value=2, max_value=10))
                        ]
                    }
                },
                "publish": {
                    "message": {
                        "oneOf": [
                            {
                                "title": faker.word(),
                                "name": faker.pystr(),
                                "payload": faker.pydict(value_types=[str, int]),
                                "x-handler": faker.pydict(value_types=[str, int]),
                            }
                            for _ in range(faker.pyint(min_value=2, max_value=10))
                        ]
                    }
                },
                "bindings": {
                    "ws": {
                        "method": faker.pystr(),
                        "query": faker.pydict(value_types=[str, int]),
                    }
                },
                "x-handlers": {
                    "connect": faker.pystr(),
                    "disconnect": faker.pystr(),
                    faker.word(): faker.pystr(),
                },
            }
        },
        "servers": {"development": {"url": "localhost"}},
    }

    forged = forge(AsyncApiSpec, data)
    assert isinstance(forged, AsyncApiSpec)
