"""
The :class:`MockAsynctionSocketIO` server is essentially
an :class:`AsynctionSocketIO` server that:

* Periodically emits events containing payloads of fake data,
  through tasks running on the background.
* Listens for all events defined in the given AsyncAPI specification,
  returning fake acknowledgmentds where applicable.
"""
import threading
from functools import partial
from pathlib import Path
from queue import Queue
from random import choice
from typing import Callable
from typing import Mapping
from typing import MutableSequence
from typing import Optional
from typing import Sequence

from faker import Faker
from faker.exceptions import UnsupportedFeature
from flask import Flask
from hypothesis import HealthCheck
from hypothesis import Phase
from hypothesis import Verbosity
from hypothesis import given
from hypothesis import settings
from hypothesis.strategies import SearchStrategy
from hypothesis.strategies import sampled_from
from hypothesis_jsonschema import from_schema
from hypothesis_jsonschema._from_schema import STRING_FORMATS

from asynction.server import AsynctionSocketIO
from asynction.types import AsyncApiSpec
from asynction.types import ErrorHandler
from asynction.types import JSONMapping
from asynction.types import JSONSchema
from asynction.types import Message
from asynction.validation import bindings_validator_factory
from asynction.validation import publish_message_validator_factory

CustomFormats = Mapping[str, SearchStrategy[str]]


def make_faker_formats(faker: Faker, sample_size: int) -> CustomFormats:
    custom_formats: CustomFormats = {}
    if sample_size < 1:
        return custom_formats

    for attr in dir(faker):
        if (
            not attr.startswith("_")
            and attr not in Faker.generator_attrs
            and attr not in STRING_FORMATS
        ):
            try:
                provider = getattr(faker, attr)
                if isinstance(provider(), str):
                    custom_formats = {
                        **custom_formats,
                        attr: sampled_from([provider() for _ in range(sample_size)]),
                    }
            except (TypeError, UnsupportedFeature):
                # Skip legacy providers or providers that require extra dependencies
                continue

    return custom_formats


def generate_fake_data_from_schema(
    schema: JSONSchema,
    custom_formats: CustomFormats,
) -> JSONMapping:
    strategy = from_schema(schema, custom_formats=custom_formats)  # type: ignore

    @given(strategy)
    @settings(
        database=None,
        max_examples=30,
        deadline=None,
        verbosity=Verbosity.quiet,
        phases=(Phase.generate,),
        suppress_health_check=HealthCheck.all(),
    )
    def example_generating_inner_function(ex):
        examples.append(ex)

    examples: MutableSequence[JSONMapping] = []
    example_generating_inner_function()
    return choice(examples)


SubscriptionTask = Callable[[], None]


def task_runner(queue: "Queue[SubscriptionTask]") -> None:
    while True:
        task = queue.get()
        task()
        queue.task_done()


def task_scheduler(
    tasks: Sequence[SubscriptionTask],
    queue: "Queue[SubscriptionTask]",
    sleep: Callable[[], None],
) -> None:
    while True:
        for task in tasks:
            queue.put(task)
            sleep()


def _noop_handler(*args, **kwargs) -> None:
    return None


class MockAsynctionSocketIO(AsynctionSocketIO):
    """Inherits the :class:`AsynctionSocketIO` class."""

    def __init__(
        self,
        spec: AsyncApiSpec,
        validation: bool,
        docs: bool,
        app: Optional[Flask],
        custom_formats_sample_size: int,
        **kwargs,
    ):
        """This is a private constructor.
        Use the :meth:`MockAsynctionSocketIO.from_spec` factory instead.
        """
        super().__init__(spec, validation=validation, docs=docs, app=app, **kwargs)
        self.faker = Faker()
        self.custom_formats = make_faker_formats(self.faker, custom_formats_sample_size)
        self._subscription_tasks: Sequence[SubscriptionTask] = []

    @classmethod
    def from_spec(
        cls,
        spec_path: Path,
        validation: bool = True,
        server_name: Optional[str] = None,
        docs: bool = True,
        default_error_handler: Optional[ErrorHandler] = None,
        app: Optional[Flask] = None,
        custom_formats_sample_size: int = 20,
        **kwargs,
    ) -> "MockAsynctionSocketIO":
        """Create a Flask-SocketIO mock server given an AsyncAPI spec.
        The server emits events containing payloads of fake data in regular intervals,
        through background subscription tasks.
        It also listens for events as per the spec definitions
        and returns mock aknowledgements where applicable.
        All event and acknowledgment payloads adhere to the schemata defined
        within the AsyncAPI spec.

        In addition to the args and kwargs of :meth:`AsynctionSocketIO.from_spec`,
        this factory method accepts some extra keyword arguments:

        * ``custom_formats_sample_size``

        :param spec_path: The path where the AsyncAPI YAML specification is located.
        :param validation: When set to ``False``, message payloads, channel
                           bindings and ack callbacks are NOT validated.
                           Defaults to ``True``.
        :param server_name: The server to pick from the AsyncAPI ``servers`` object.
                            The server object is then used to configure
                            the path ``kwarg`` of the SocketIO server.
        :param docs: When set to ``True``, HTML rendered documentation is generated
                     and served through the ``GET {base_path}/docs`` route of the app.
                     The ``GET {base_path}/docs/asyncapi.json`` route is also exposed,
                     returning the raw specification data for programmatic retrieval.
                     Defaults to ``True``.
        :param default_error_handler: The error handler that handles any namespace
                                      without an explicit error handler.
                                      Equivelant of ``@socketio.on_error_default``
        :param app: The flask application instance. Defaults to ``None``.
        :param custom_formats_sample_size: The ammout of the Faker provider samples
                                           to be used for each custom string format.
                                           Hypotheses uses these samples to generate
                                           fake data. Set to ``0`` if custom formats
                                           are not needed.
                                           Defaults to ``20``.
        :param kwargs: Flask-SocketIO, Socket.IO and Engine.IO server options.

        :returns: A Flask-SocketIO mock server, emitting events of fake data in
                  regular intervals.
                  The server also has mock event and error handlers registered.

        Example::

            mock_asio = MockAsynctionSocketIO.from_spec(
                spec_path="./docs/asyncapi.yaml",
                app=flask_app,
                # any other kwarg that the flask_socketio.SocketIO constructor accepts
            )

        """
        return super().from_spec(
            spec_path,
            validation=validation,
            server_name=server_name,
            docs=docs,
            default_error_handler=default_error_handler,
            app=app,
            custom_formats_sample_size=custom_formats_sample_size,
            **kwargs,
        )

    def _register_handlers(
        self, default_error_handler: Optional[ErrorHandler] = None
    ) -> None:
        for namespace, channel in self.spec.channels.items():
            if channel.publish is not None:
                for message in channel.publish.message.oneOf:
                    handler = self.make_publish_handler(message)

                    if self.validation:
                        with_payload_validation = publish_message_validator_factory(
                            message=message
                        )
                        handler = with_payload_validation(handler)

                    self.on_event(message.name, handler, namespace)

            if channel.subscribe is not None:
                self._subscription_tasks = [
                    *self._subscription_tasks,
                    *[
                        self.make_subscription_task(message, namespace)
                        for message in channel.subscribe.message.oneOf
                    ],
                ]

            connect_handler = _noop_handler

            if self.validation:
                with_bindings_validation = bindings_validator_factory(channel.bindings)
                connect_handler = with_bindings_validation(connect_handler)

            self.on_event("connect", connect_handler, namespace)

        if default_error_handler is not None:
            self.on_error_default(default_error_handler)

    def make_subscription_task(
        self, message: Message, namespace: str
    ) -> SubscriptionTask:
        def task() -> None:
            self.emit(
                message.name,
                generate_fake_data_from_schema(
                    message.payload or {"type": "null"}, self.custom_formats
                ),
                namespace=namespace,
                callback=message.x_ack and _noop_handler,
            )

        return task

    def make_publish_handler(self, message: Message) -> Callable:
        if message.x_ack is not None:

            def handler(*args, **kwargs):
                return generate_fake_data_from_schema(
                    message.x_ack.args, self.custom_formats
                )

            return handler

        return _noop_handler

    def start_background_task(
        self, target: Callable, *args, **kwargs
    ) -> threading.Thread:

        # The tasks created in the :meth:`MockAsynctionSocketIO.run` method below
        # (both runner and scheduler) MUST be daemonic.
        # However, python-engineio does not support daemonic background tasks,
        # unless the chosen async mode defaults to some daemon-like behaviour.
        # Native threads have daemon set to False by default, which is rather
        # inconvinient for this use case.
        # See the relevant issue:
        # https://github.com/miguelgrinberg/python-engineio/issues/244
        #
        # The current method is a hack that accounts for the threading scenario,
        # to ensure that native threads are started as daemons.

        if self.async_mode == "threading":
            th = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
            th.start()
            return th

        return super().start_background_task(target, *args, **kwargs)

    def run(
        self,
        app: Flask,
        host: Optional[str] = None,
        port: Optional[int] = None,
        subscription_task_interval: float = 1.0,
        max_worker_number: int = 8,
        **kwargs,
    ) -> None:
        """
        Run the mock Asynction SocketIO web server.

        In addition to the args and kwargs of :meth:`flask_socketio.SocketIO.run`,
        this method accepts some extra keyword arguments:

        * ``subscription_task_interval``
        * ``max_worker_number``

        :param app: The flask application instance.
        :param host: The hostname or IP address for the server to listen on.
                     Defaults to ``127.0.0.1``.
        :param port: The port number for the server to listen on. Defaults to
                     ``5000``.
        :param subscription_task_interval: How often (in seconds) a subscription task
                                           (thread that emits an event to
                                           a connected client) is scheduled.
                                           Defaults to ``1.0``.
        :param max_worker_number: The maximum number of workers to be started for the
                                  purposes of executing background subscription tasks.
                                  Defaults to ``8``.
        :param kwargs: Additional web server options that are propagated to
                       :meth:`flask_socketio.SocketIO.run`. The web server options
                       are specific to the server used in each of the supported
                       async modes. Refer to the Flask-SocketIO docs for details.
        """
        queue: "Queue[SubscriptionTask]" = self.server.eio.create_queue()

        for _ in range(min(max_worker_number, len(self._subscription_tasks))):
            _ = self.start_background_task(task_runner, queue=queue)

        _ = self.start_background_task(
            task_scheduler,
            tasks=self._subscription_tasks,
            queue=queue,
            sleep=partial(self.sleep, subscription_task_interval),
        )

        return super().run(app, host=host, port=port, **kwargs)
