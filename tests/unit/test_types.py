import pytest
from faker import Faker
from svarog import forge

from asynction.types import GLOBAL_NAMESPACE
from asynction.types import ApiKeyLocation
from asynction.types import AsyncApiSpec
from asynction.types import Channel
from asynction.types import ChannelBindings
from asynction.types import ChannelHandlers
from asynction.types import Message
from asynction.types import OAuth2Flow
from asynction.types import OAuth2Flows
from asynction.types import OneOfMessages
from asynction.types import Operation
from asynction.types import SecurityScheme
from asynction.types import SecuritySchemesType


def test_message_deserialisation(faker: Faker):
    name = faker.pystr()
    payload = faker.pydict(value_types=[str, int])
    x_handler = faker.pystr()
    x_ack_args = faker.pydict(value_types=[str, int])

    message = forge(
        Message,
        {
            "name": name,
            "payload": payload,
            "x-handler": x_handler,
            "x-ack": {"args": x_ack_args},
        },
    )

    assert message.name == name
    assert message.payload == payload
    assert message.x_handler == x_handler
    assert message.x_ack
    assert message.x_ack.args == x_ack_args


def test_message_deserialisation_with_missing_fields(faker: Faker):
    name = faker.pystr()
    message = forge(
        Message,
        {"name": name},
    )

    assert message.name == name
    assert message.payload is None
    assert message.x_handler is None
    assert message.x_ack is None


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
    assert len(one_of_messages.one_of) == n


def test_one_of_messages_deserialisation_of_message_structure(faker: Faker):
    name = faker.pystr()
    payload = faker.pydict(value_types=[str, int])
    x_handler = faker.pystr()
    data = {"name": name, "payload": payload, "x-handler": x_handler}

    one_of_messages = forge(OneOfMessages, data)
    assert len(one_of_messages.one_of) == 1
    assert one_of_messages.one_of[0].name == name
    assert one_of_messages.one_of[0].payload == payload
    assert one_of_messages.one_of[0].x_handler == x_handler


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
        "x-security": [{"basic": []}],
    }

    channel = forge(Channel, data)
    assert isinstance(channel.publish, Operation)
    assert isinstance(channel.subscribe, Operation)
    assert isinstance(channel.bindings, ChannelBindings)
    assert isinstance(channel.x_handlers, ChannelHandlers)
    assert isinstance(channel.x_security, list)
    assert len(channel.x_security) == 1
    assert "basic" in channel.x_security[0]
    assert isinstance(channel.x_security[0]["basic"], list)
    assert len(channel.x_security[0]["basic"]) == 0


def test_channel_raises_value_error_if_publish_messages_miss_handler(faker: Faker):
    with pytest.raises(ValueError):
        Channel(
            subscribe=Operation(
                message=OneOfMessages(
                    one_of=[
                        Message(
                            name=faker.pystr(),
                            payload=faker.pydict(value_types=[str, int]),
                        )
                    ]
                )
            ),
            publish=Operation(
                message=OneOfMessages(
                    one_of=[
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


def test_async_api_spec_from_and_to_dict(faker: Faker):
    data = {
        "asyncapi": "2.3.0",
        "info": {
            "title": faker.sentence(),
            "version": faker.pystr(),
            "description": faker.sentence(),
        },
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
                                "x-ack": {
                                    "args": faker.pydict(value_types=[str, int]),
                                },
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
        "servers": {
            "development": {
                "url": "localhost",
                "protocol": "ws",
                "security": [{"test": []}],
            }
        },
        "components": {
            "securitySchemes": {
                "test": {"type": "http", "scheme": "basic"},
                "test2": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                "testApiKey": {"type": "httpApiKey", "name": "test", "in": "header"},
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://localhost:12345",
                            "refreshUrl": "https://localhost:12345/refresh",
                            "scopes": {"a": "A", "b": "B"},
                        }
                    },
                },
            }
        },
    }

    spec = AsyncApiSpec.from_dict(data)
    assert isinstance(spec, AsyncApiSpec)
    assert spec.to_dict() == data


def test_oauth2_implicit_flow_validation():
    scopes = {"a": "A", "b": "B"}
    # authorization_url is required for implicit flow
    flow = OAuth2Flow(scopes=scopes, authorization_url=None)

    with pytest.raises(ValueError):
        OAuth2Flows(implicit=flow)


def test_oauth2_password_flow_validation():
    scopes = {"a": "A", "b": "B"}
    # token_url is required for password flow
    flow = OAuth2Flow(scopes=scopes, token_url=None)

    with pytest.raises(ValueError):
        OAuth2Flows(password=flow)


def test_oauth2_client_credentials_flow_validation():
    scopes = {"a": "A", "b": "B"}
    # token_url is required for client_credentials flow
    flow = OAuth2Flow(scopes=scopes, token_url=None)

    with pytest.raises(ValueError):
        OAuth2Flows(client_credentials=flow)


def test_oauth2_authorization_code_flow_validation():
    scopes = {"a": "A", "b": "B"}
    # token_url is required for authorization_code flow
    flow = OAuth2Flow(scopes=scopes, token_url=None)

    with pytest.raises(ValueError):
        OAuth2Flows(authorization_code=flow)


def test_security_scheme_validation():
    with pytest.raises(ValueError):
        # missing flows
        SecurityScheme(type=SecuritySchemesType.OAUTH2)

    with pytest.raises(ValueError):
        # missing flows
        SecurityScheme(type=SecuritySchemesType.OPENID_CONNECT)

    with pytest.raises(ValueError):
        # missing scheme
        SecurityScheme(type=SecuritySchemesType.HTTP)

    with pytest.raises(ValueError):
        # missing in
        SecurityScheme(type=SecuritySchemesType.HTTP_API_KEY)
    with pytest.raises(ValueError):
        # missing name
        SecurityScheme(type=SecuritySchemesType.HTTP_API_KEY, in_=ApiKeyLocation.HEADER)


def test_asyncapi_spec_validation_invalid_security_requirement(faker: Faker):
    data = {
        "asyncapi": "2.3.0",
        "info": {
            "title": faker.sentence(),
            "version": faker.pystr(),
            "description": faker.sentence(),
        },
        "channels": {},
        "servers": {
            "development": {
                "url": "localhost",
                "protocol": "ws",
                "security": [{"test": [], "invalid": "A"}],
            }
        },
        "components": {
            "securitySchemes": {
                "test": {"type": "http", "scheme": "basic"},
                "test2": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                "testApiKey": {"type": "httpApiKey", "name": "test", "in": "header"},
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://localhost:12345",
                            "refreshUrl": "https://localhost:12345/refresh",
                            "scopes": {"a": "A", "b": "B"},
                        }
                    },
                },
            }
        },
    }
    with pytest.raises(ValueError):
        # missing security scheme
        AsyncApiSpec.from_dict(data)


def test_asyncapi_spec_validation_invalid_security_requirement_scopes(faker: Faker):
    data = {
        "asyncapi": "2.3.0",
        "info": {
            "title": faker.sentence(),
            "version": faker.pystr(),
            "description": faker.sentence(),
        },
        "channels": {},
        "servers": {
            "development": {
                "url": "localhost",
                "protocol": "ws",
                "security": [{"test": ["a"]}],
            }
        },
        "components": {
            "securitySchemes": {
                "test": {"type": "http", "scheme": "basic"},
                "test2": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                "testApiKey": {"type": "httpApiKey", "name": "test", "in": "header"},
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://localhost:12345",
                            "refreshUrl": "https://localhost:12345/refresh",
                            "scopes": {"a": "A", "b": "B"},
                        }
                    },
                },
            }
        },
    }
    with pytest.raises(ValueError):
        # missing security scheme
        AsyncApiSpec.from_dict(data)


def test_asyncapi_spec_validation_invalid_security_requirement_undefined_scopes(
    faker: Faker,
):
    data = {
        "asyncapi": "2.3.0",
        "info": {
            "title": faker.sentence(),
            "version": faker.pystr(),
            "description": faker.sentence(),
        },
        "channels": {},
        "servers": {
            "development": {
                "url": "localhost",
                "protocol": "ws",
                "security": [{"oauth2": ["undefined"]}],
            }
        },
        "components": {
            "securitySchemes": {
                "test": {"type": "http", "scheme": "basic"},
                "test2": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                "testApiKey": {"type": "httpApiKey", "name": "test", "in": "header"},
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://localhost:12345",
                            "refreshUrl": "https://localhost:12345/refresh",
                            "scopes": {"a": "A", "b": "B"},
                        }
                    },
                },
            }
        },
    }
    with pytest.raises(ValueError):
        # missing security scheme
        AsyncApiSpec.from_dict(data)


def test_asyncapi_spec_validation_invalid_security_requirement_on_namespace(
    faker: Faker,
):
    data = {
        "asyncapi": "2.3.0",
        "info": {
            "title": faker.sentence(),
            "version": faker.pystr(),
            "description": faker.sentence(),
        },
        "channels": {
            GLOBAL_NAMESPACE: {
                "x-security": [{"oauth2": ["undefined"]}],
            }
        },
        "servers": {
            "development": {
                "url": "localhost",
                "protocol": "ws",
            }
        },
        "components": {
            "securitySchemes": {
                "test": {"type": "http", "scheme": "basic"},
                "test2": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                "testApiKey": {"type": "httpApiKey", "name": "test", "in": "header"},
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://localhost:12345",
                            "refreshUrl": "https://localhost:12345/refresh",
                            "scopes": {"a": "A", "b": "B"},
                        }
                    },
                },
            }
        },
    }
    with pytest.raises(ValueError):
        # missing security scheme
        AsyncApiSpec.from_dict(data)


def test_asyncapi_spec_validation_missing_security_scheme(faker: Faker):
    data = {
        "asyncapi": "2.3.0",
        "info": {
            "title": faker.sentence(),
            "version": faker.pystr(),
            "description": faker.sentence(),
        },
        "channels": {},
        "servers": {
            "development": {
                "url": "localhost",
                "protocol": "ws",
                "security": [{"test": []}],
            }
        },
    }
    with pytest.raises(ValueError):
        # missing security scheme
        AsyncApiSpec.from_dict(data)
