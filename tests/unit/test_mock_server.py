import threading
from ipaddress import IPv4Address
from typing import Any
from typing import Callable
from typing import Mapping
from typing import MutableSequence
from typing import Optional
from typing import Sequence
from unittest.mock import ANY
from unittest.mock import patch
from uuid import uuid4

import jsonschema
import pytest
from faker import Faker
from flask.app import Flask
from flask_socketio import SocketIO
from hypothesis.strategies import sampled_from
from hypothesis.strategies._internal.strategies import SearchStrategy
from hypothesis_jsonschema._from_schema import STRING_FORMATS

from asynction import PayloadValidationException
from asynction.exceptions import BindingsValidationException
from asynction.exceptions import SecurityException
from asynction.mock_server import MockAsynctionSocketIO
from asynction.mock_server import generate_fake_data_from_schema
from asynction.mock_server import make_faker_formats
from asynction.mock_server import task_runner
from asynction.mock_server import task_scheduler
from asynction.server import AsynctionSocketIO
from asynction.server import _noop_handler
from asynction.types import GLOBAL_NAMESPACE
from asynction.types import AsyncApiSpec
from asynction.types import Channel
from asynction.types import ChannelBindings
from asynction.types import ChannelHandlers
from asynction.types import Components
from asynction.types import ErrorHandler
from asynction.types import HTTPAuthenticationScheme
from asynction.types import Info
from asynction.types import Message
from asynction.types import MessageAck
from asynction.types import OneOfMessages
from asynction.types import Operation
from asynction.types import SecurityScheme
from asynction.types import SecuritySchemesType
from asynction.types import Server
from asynction.types import ServerProtocol
from asynction.types import WebSocketsChannelBindings
from tests.fixtures import FixturePaths
from tests.utils import deep_unwrap


def test_make_faker_formats_with_non_positive_sample_size(faker: Faker):
    assert make_faker_formats(faker, 0) == {}


def test_make_fkr_formats_with_positive_sample_size_gives_strategies_of_str_providers(
    faker: Faker,
):
    sample_size = faker.pyint(min_value=2, max_value=6)
    with patch.object(
        faker, "first_name", return_value=faker.pystr()
    ) as first_name_mock:
        with patch.object(
            faker, "last_name", return_value=faker.pyint()
        ) as last_name_mock:

            custom_formats = make_faker_formats(faker, sample_size)

            # Extra call is theere to check the provider return type
            assert first_name_mock.call_count == sample_size + 1

            # Providers that do not generate str values should not be included
            assert last_name_mock.call_count == 1
            assert "lase_name" not in custom_formats

            for format_name, strategy in custom_formats.items():
                assert format_name not in Faker.generator_attrs
                assert hasattr(faker, format_name)

                # Providers that match pre-existing default JSONSchema formats
                # should not be included:
                assert format_name not in STRING_FORMATS

                assert isinstance(strategy, SearchStrategy)


def test_generate_fake_data_from_schema_str():
    fake_data = generate_fake_data_from_schema({"type": "string"}, custom_formats={})
    assert isinstance(fake_data, str)


def test_generate_fake_data_from_schema_number():
    fake_data = generate_fake_data_from_schema({"type": "number"}, custom_formats={})
    assert isinstance(fake_data, (int, float))


def test_generate_fake_data_from_schema_dict():
    fake_data = generate_fake_data_from_schema(
        {
            "type": "object",
            "properties": {"foo": {"type": "string"}, "bar": {"type": "boolean"}},
            "required": ["foo", "bar"],
        },
        custom_formats={},
    )
    assert isinstance(fake_data, dict)

    assert "foo" in fake_data
    assert isinstance(fake_data["foo"], str)
    assert "bar" in fake_data
    assert isinstance(fake_data["bar"], bool)


def test_generate_fake_data_from_schema_using_default_format():
    fake_data = generate_fake_data_from_schema(
        {"type": "string", "format": "ipv4"}, custom_formats={}
    )
    fake_ip = IPv4Address(fake_data)
    assert isinstance(fake_ip, IPv4Address)


def test_generate_fake_data_from_schema_using_custom_formats(faker: Faker):
    custom_format_name = str(uuid4())
    fake_value = str(uuid4())
    custom_formats = {custom_format_name: sampled_from([fake_value])}

    for _ in range(faker.pyint(min_value=3, max_value=10)):
        fake_data = generate_fake_data_from_schema(
            {"type": "string", "format": custom_format_name},
            custom_formats=custom_formats,
        )
        assert fake_data == fake_value


def test_mock_asynction_socketio_from_spec(fixture_paths: FixturePaths):
    mock_asio = MockAsynctionSocketIO.from_spec(spec_path=fixture_paths.simple)
    assert isinstance(mock_asio, MockAsynctionSocketIO)
    assert isinstance(mock_asio.faker, Faker)


def new_mock_asynction_socket_io(
    spec: AsyncApiSpec,
    app: Optional[Flask] = None,
    async_mode: str = "threading",
) -> MockAsynctionSocketIO:
    return MockAsynctionSocketIO(
        spec=spec,
        validation=True,
        docs=True,
        app=app,
        custom_formats_sample_size=20,
        async_mode=async_mode,
    )


def test_register_handlers_registers_noop_handler_for_message_with_no_ack(
    server_info: Info,
    faker: Faker,
):
    namespace = f"/{faker.pystr()}"
    event_name = faker.word()
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                publish=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "object"},
                                x_handler=faker.pystr(),
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = new_mock_asynction_socket_io(spec)

    server._register_handlers()
    assert len(server.handlers) == 2  # connect handler included as well
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == event_name
    assert registered_namespace == namespace
    handler = deep_unwrap(registered_handler)
    assert handler == _noop_handler


def test_register_handlers_registers_valid_handler_for_message_with_ack(
    server_info: Info, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    event_name = faker.word()
    ack_schema = {
        "type": "object",
        "properties": {
            "foo": {
                "type": "string",
                "enum": [faker.pystr(), faker.pystr()],
            },
            "bar": {
                "type": "number",
                "minimum": 10,
                "maximum": 20,
            },
        },
        "required": ["foo", "bar"],
    }
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                publish=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=event_name,
                                payload={"type": "object"},
                                x_handler=faker.pystr(),
                                x_ack=MessageAck(args=ack_schema),
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = new_mock_asynction_socket_io(spec)

    server._register_handlers()
    assert len(server.handlers) == 2  # connect handler included as well
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == event_name
    assert registered_namespace == namespace
    handler = deep_unwrap(registered_handler)

    ack = handler(faker.pydict())
    jsonschema.validate(ack, ack_schema)
    assert True


def test_register_handlers_adds_payload_validator_if_validation_is_enabled(
    server_info: Info,
    faker: Faker,
):
    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                publish=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=faker.word(),
                                payload={"type": "string"},
                                x_handler=faker.pystr(),
                            )
                        ]
                    ),
                )
            )
        },
    )
    server = new_mock_asynction_socket_io(spec)

    server._register_handlers()
    _, registered_handler, _ = server.handlers[0]
    handler_with_validation = deep_unwrap(registered_handler, depth=1)
    actual_handler = deep_unwrap(handler_with_validation)
    args = (faker.pyint(),)

    actual_handler(*args)  # actual handler does not raise validation errors
    with pytest.raises(PayloadValidationException):
        handler_with_validation(*args)


def test_register_handlers_registers_connection_handler(
    server_info: Info, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(), info=server_info, channels={namespace: Channel()}
    )
    server = new_mock_asynction_socket_io(spec)

    server._register_handlers()

    assert len(server.handlers) == 1
    registered_event, registered_handler, registered_namespace = server.handlers[0]
    assert registered_event == "connect"
    assert deep_unwrap(registered_handler) == _noop_handler
    assert registered_namespace == namespace


def test_register_handlers_registers_connection_handler_with_bindings_validation(
    server_info: Info,
    faker: Faker,
):
    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                bindings=ChannelBindings(
                    ws=WebSocketsChannelBindings(
                        method="GET",
                    )
                ),
            )
        },
    )
    server = new_mock_asynction_socket_io(spec)
    flask_app = Flask(__name__)

    server._register_handlers()
    _, registered_handler, _ = server.handlers[0]

    handler_with_validation = deep_unwrap(registered_handler, depth=1)
    actual_handler = deep_unwrap(registered_handler)

    with flask_app.test_client() as c:
        with patch.object(server, "start_background_task"):
            c.post()  # Inject invalid POST request
            actual_handler()  # actual handler does not raise validation errors
            with pytest.raises(BindingsValidationException):
                handler_with_validation()


def test_register_namespace_handlers_emits_security_validator_if_security_enabled():
    channel_handlers = ChannelHandlers(connect="tests.fixtures.handlers.connect")
    spec = AsyncApiSpec(
        asyncapi="2.2.0",
        info=Info("test", "1.0.0"),
        servers={
            "test": Server("https://localhost/", ServerProtocol.WSS, [{"basic": []}])
        },
        channels={GLOBAL_NAMESPACE: Channel(x_handlers=channel_handlers)},
        components=Components(
            security_schemes={
                "basic": SecurityScheme(
                    type=SecuritySchemesType.HTTP,
                    scheme=HTTPAuthenticationScheme.BASIC,
                    x_basic_info_func="tests.fixtures.handlers.basic_info",
                )
            }
        ),
    )

    server = new_mock_asynction_socket_io(spec)
    server._register_handlers(server_security=server.spec.servers.get("test").security)
    event_name, registered_handler, _ = server.handlers[0]
    assert event_name == "connect"
    handler_with_security = deep_unwrap(registered_handler, depth=1)
    actual_handler = deep_unwrap(handler_with_security)

    with Flask(__name__).test_client() as c:
        c.post()  # Inject invalid POST request
        actual_handler()
        with pytest.raises(SecurityException):
            handler_with_security()  # handler raises security exception
            assert True


def test_register_namespace_handlers_emits_security_if_security_enabled_on_namespace():
    channel_handlers = ChannelHandlers(connect="tests.fixtures.handlers.connect")
    spec = AsyncApiSpec(
        asyncapi="2.2.0",
        info=Info("test", "1.0.0"),
        servers={"test": Server("https://localhost/", ServerProtocol.WSS, [])},
        channels={
            GLOBAL_NAMESPACE: Channel(
                x_handlers=channel_handlers, x_security=[{"basic": []}]
            )
        },
        components=Components(
            security_schemes={
                "basic": SecurityScheme(
                    type=SecuritySchemesType.HTTP,
                    scheme=HTTPAuthenticationScheme.BASIC,
                    x_basic_info_func="tests.fixtures.handlers.basic_info",
                )
            }
        ),
    )

    server = new_mock_asynction_socket_io(spec)
    server._register_handlers(server_security=server.spec.servers.get("test").security)
    event_name, registered_handler, _ = server.handlers[0]
    assert event_name == "connect"
    handler_with_security = deep_unwrap(registered_handler, depth=1)
    actual_handler = deep_unwrap(handler_with_security)

    with Flask(__name__).test_client() as c:
        c.post()  # Inject invalid POST request
        actual_handler()
        with pytest.raises(SecurityException):
            handler_with_security()  # handler raises security exception
            assert True


@pytest.mark.parametrize(
    argnames=["optional_error_handler"],
    argvalues=[[lambda _: None], [None]],
    ids=["with_default_error_handler", "without_default_error_handler"],
)
def test_register_handlers_registers_default_error_handler(
    optional_error_handler: Optional[ErrorHandler], server_info: Info, faker: Faker
):
    server = new_mock_asynction_socket_io(
        AsyncApiSpec(asyncapi=faker.pystr(), info=server_info, channels={})
    )

    server._register_handlers(default_error_handler=optional_error_handler)
    assert server.default_exception_handler == optional_error_handler


class MockThread:
    def __init__(self, target: Callable, args: Sequence, kwargs: Mapping[str, Any]):
        self.target = target
        self.args = args
        self.kwargs = kwargs


def test_run_spawns_background_tasks_and_calls_super_run(
    server_info: Info, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=faker.word(),
                                payload={"type": "string"},
                            )
                        ]
                    ),
                )
            )
        },
    )
    flask_app = Flask(__name__)
    server = new_mock_asynction_socket_io(spec, flask_app)
    server._register_handlers()

    background_tasks: MutableSequence[MockThread] = []

    def start_background_task_mock(target, *args, **kwargs):
        mt = MockThread(target=target, args=args, kwargs=kwargs)
        background_tasks.append(mt)
        return mt

    with patch.object(SocketIO, "run") as super_run_mock:
        with patch.object(server, "start_background_task", start_background_task_mock):
            server.run(flask_app)

            assert len(background_tasks) == 2
            assert background_tasks[0].target == task_runner
            assert background_tasks[-1].target == task_scheduler

            super_run_mock.assert_called_once_with(flask_app, host=None, port=None)


def test_run_respects_maximum_number_of_workers(server_info: Info, faker: Faker):
    max_worker_number = faker.pyint(min_value=2, max_value=5)
    sub_messages_number = max_worker_number + faker.pyint(min_value=3, max_value=6)

    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=faker.word(),
                                payload={"type": "string"},
                            )
                            for _ in range(sub_messages_number)
                        ]
                    ),
                )
            )
        },
    )
    background_tasks: MutableSequence[MockThread] = []

    def start_background_task_mock(target, *args, **kwargs):
        mt = MockThread(target=target, args=args, kwargs=kwargs)
        background_tasks.append(mt)
        return mt

    flask_app = Flask(__name__)
    server = new_mock_asynction_socket_io(spec, flask_app)
    server._register_handlers()

    with patch.object(SocketIO, "run"):
        with patch.object(server, "start_background_task", start_background_task_mock):
            server.run(flask_app, max_worker_number=max_worker_number)

            assert len(background_tasks) == max_worker_number + 1


def test_run_spawns_minimum_number_of_workers(server_info: Info, faker: Faker):
    max_worker_number = faker.pyint(min_value=8, max_value=15)
    sub_messages_number = max_worker_number - faker.pyint(min_value=3, max_value=5)

    namespace = f"/{faker.pystr()}"
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(
                        oneOf=[
                            Message(
                                name=faker.word(),
                                payload={"type": "string"},
                            )
                            for _ in range(sub_messages_number)
                        ]
                    ),
                )
            )
        },
    )

    background_tasks: MutableSequence[MockThread] = []

    def start_background_task_mock(target, *args, **kwargs):
        mt = MockThread(target=target, args=args, kwargs=kwargs)
        background_tasks.append(mt)
        return mt

    flask_app = Flask(__name__)
    server = new_mock_asynction_socket_io(spec, flask_app)
    server._register_handlers()

    with patch.object(SocketIO, "run"):
        with patch.object(server, "start_background_task", start_background_task_mock):
            server.run(flask_app, max_worker_number=max_worker_number)

            assert len(background_tasks) == sub_messages_number + 1


def test_make_subscription_task_with_message_payload_and_ack(
    server_info: Info, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    message = Message(
        name=faker.word(),
        payload={
            "type": "object",
            "properties": {
                "foo": {
                    "type": "string",
                    "enum": [faker.pystr(), faker.pystr()],
                },
                "bar": {
                    "type": "number",
                    "minimum": 10,
                    "maximum": 20,
                },
            },
            "required": ["foo", "bar"],
        },
        x_ack=MessageAck(
            args={
                "type": "string",
                "enum": [faker.pystr(), faker.pystr()],
            }
        ),
    )
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(oneOf=[message]),
                )
            )
        },
    )
    server = new_mock_asynction_socket_io(spec)
    task = server.make_subscription_task(message=message, namespace=namespace)

    with patch.object(server, "emit") as emit_mock:
        task()
        emit_mock.assert_called_once_with(
            message.name, ANY, namespace=namespace, callback=_noop_handler
        )
        _, data = emit_mock.call_args[0]
        jsonschema.validate(data, message.payload)
        assert True


def test_make_subscription_task_with_no_message_payload_but_ack(
    server_info: Info, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    message = Message(
        name=faker.word(),
        x_ack=MessageAck(
            args={
                "type": "string",
                "enum": [faker.pystr(), faker.pystr()],
            }
        ),
    )
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(oneOf=[message]),
                )
            )
        },
    )
    server = new_mock_asynction_socket_io(spec)
    task = server.make_subscription_task(message=message, namespace=namespace)

    with patch.object(server, "emit") as emit_mock:
        task()
        emit_mock.assert_called_once_with(
            message.name, None, namespace=namespace, callback=_noop_handler
        )


def test_make_subscription_task_with_message_payload_but_no_ack(
    server_info: Info, faker: Faker
):
    namespace = f"/{faker.pystr()}"
    message = Message(
        name=faker.word(),
        payload={
            "type": "string",
            "enum": [faker.pystr(), faker.pystr()],
        },
    )
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={
            namespace: Channel(
                subscribe=Operation(
                    message=OneOfMessages(oneOf=[message]),
                )
            )
        },
    )
    server = new_mock_asynction_socket_io(spec)
    task = server.make_subscription_task(message=message, namespace=namespace)

    with patch.object(server, "emit") as emit_mock:
        task()
        emit_mock.assert_called_once_with(
            message.name, ANY, namespace=namespace, callback=None
        )
        _, data = emit_mock.call_args[0]
        jsonschema.validate(data, message.payload)
        assert True


def test_start_background_daemon_task_with_threading_async_mode(
    server_info: Info, faker: Faker
):
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={f"/{faker.pystr()}": Channel()},
    )
    server = new_mock_asynction_socket_io(
        spec, app=Flask(__name__), async_mode="threading"
    )

    def target():
        # noop
        pass

    args = tuple(faker.pylist())
    kwargs = faker.pydict()

    with patch.object(threading, "Thread") as mock_thread_cls:
        t = server.start_background_task(target, *args, **kwargs)

        mock_thread_cls.assert_called_once_with(
            target=target, args=args, kwargs=kwargs, daemon=True
        )
        t.start.assert_called_once_with()  # type: ignore


def test_start_background_daemon_task_with_non_threading_async_mode(
    server_info: Info, faker: Faker
):
    spec = AsyncApiSpec(
        asyncapi=faker.pystr(),
        info=server_info,
        channels={f"/{faker.pystr()}": Channel()},
    )
    server = new_mock_asynction_socket_io(spec, app=Flask(__name__))

    server.async_mode = "gevent"

    def target():
        # noop
        pass

    args = tuple(faker.pylist())
    kwargs = faker.pydict()

    with patch.object(AsynctionSocketIO, "start_background_task") as super_mock:
        server.start_background_task(target, *args, **kwargs)

        super_mock.assert_called_once_with(target, *args, **kwargs)
