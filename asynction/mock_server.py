"""
The :class:`MockAsynctionSocketIO` server is essentially
an :class:`AsynctionSocketIO` server that:

* Periodically emits events containing payloads of fake data,
  through tasks running on the background.
* Listens for all events defined in the given AsyncAPI specification,
  returning fake acknowledgmentds where applicable.
"""
import threading
from pathlib import Path
from queue import Queue
from random import choice
from typing import Callable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence

from faker import Faker
from faker.exceptions import UnsupportedFeature
from flask.app import Flask
from flask_socketio import SocketIO
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

    examples: List[JSONMapping] = []
    example_generating_inner_function()
    return choice(examples)


SubscriptionTask = Callable[[], None]


def task_runner(queue: "Queue[SubscriptionTask]") -> None:
    while True:
        task = queue.get()
        task()
        queue.task_done()


def task_scheduler(
    server: "MockAsynctionSocketIO",
    tasks: Sequence[SubscriptionTask],
    queue: "Queue[SubscriptionTask]",
    event: threading.Event,
) -> None:
    while True:
        for task in tasks:
            if not event.is_set():
                return
            queue.put(task)
            server.sleep(server.subscription_task_interval)


class MockAsynctionSocketIO(AsynctionSocketIO):
    """Inherits the :class:`AsynctionSocketIO` class."""

    def __init__(
        self,
        spec: AsyncApiSpec,
        validation: bool,
        app: Optional[Flask],
        subscription_task_interval: int,
        max_worker_number: int,
        custom_formats_sample_size: int,
        **kwargs
    ):
        """This is a private constructor.
        Use the :meth:`MockAsynctionSocketIO.from_spec` factory instead.
        """
        super().__init__(spec, validation=validation, app=app, **kwargs)
        self.subscription_task_interval = subscription_task_interval
        self.max_worker_number = max_worker_number
        self.faker = Faker()
        self.custom_formats = make_faker_formats(self.faker, custom_formats_sample_size)

    @classmethod
    def from_spec(
        cls,
        spec_path: Path,
        validation: bool = True,
        server_name: Optional[str] = None,
        default_error_handler: Optional[ErrorHandler] = None,
        app: Optional[Flask] = None,
        subscription_task_interval: int = 1,
        max_worker_number: int = 8,
        custom_formats_sample_size: int = 20,
        **kwargs
    ) -> SocketIO:
        """Create a Flask-SocketIO mock server given an AsyncAPI spec.
        The server emits events containing payloads of fake data in regular intervals,
        through background subscription tasks.
        It also listens for events as per the spec definitions
        and returns mock aknowledgements where applicable.
        All event and acknowledgment payloads adhere to the schemata defined
        within the AsyncAPI spec.

        In addition to the args and kwargs of :meth:`AsynctionSocketIO.from_spec`,
        this factory method accepts some extra keyword arguments:

        * ``subscription_task_interval``
        * ``max_worker_number``
        * ``custom_formats_sample_size``

        :param spec_path: The path where the AsyncAPI YAML specification is located.
        :param validation: When set to ``False``, message payloads, channel
                           bindings and ack callbacks are NOT validated.
                           Defaults to ``True``.
        :param server_name: The server to pick from the AsyncAPI ``servers`` object.
                            The server object is then used to configure
                            the path ``kwarg`` of the SocketIO server.
        :param default_error_handler: The error handler that handles any namespace
                                      without an explicit error handler.
                                      Equivelant of ``@socketio.on_error_default``
        :param app: The flask application instance. Defaults to ``None``.
        :param subscription_task_interval: How often (in seconds) a subscription task
                                           (thread that emits an event to
                                           a connected client) is scheduled.
                                           Defaults to ``1``.
        :param max_worker_number: The maximum number of workers to be started for the
                                  purposes of executing background subscription tasks.
                                  Defaults to ``8``.
        :param custom_formats_sample_size: The ammout of the Faker provider samples
                                           to be used for each custom string format.
                                           Hypotheses uses these samples to generate
                                           fake data. Set to ``0`` if custom formats
                                           are not needed.
                                           Defaults to ``20``.
        :param kwargs: Flask-SocketIO, Socket.IO and Engine.IO server options.

        :returns: A Flask-SocketIO mock server, emitting events with fake data in
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
            default_error_handler=default_error_handler,
            app=app,
            subscription_task_interval=subscription_task_interval,
            max_worker_number=max_worker_number,
            custom_formats_sample_size=custom_formats_sample_size,
            **kwargs
        )

    def _register_connection_handler(
        self, namespace: str, subscription_tasks: Sequence[SubscriptionTask]
    ) -> None:
        queue: "Queue[SubscriptionTask]" = self.server.eio.create_queue()
        event: threading.Event = self.server.eio.create_event()

        def connect_handler() -> None:
            event.set()
            for _ in range(min(self.max_worker_number, len(subscription_tasks))):
                t: threading.Thread = self.start_background_task(
                    task_runner, queue=queue
                )
                t.daemon = True

            scheduler_t: threading.Thread = self.start_background_task(
                task_scheduler,
                server=self,
                tasks=subscription_tasks,
                queue=queue,
                event=event,
            )
            scheduler_t.daemon = True

        def disconnect_handler() -> None:
            event.clear()

        self.on_event("connect", connect_handler, namespace)
        self.on_event("disconnect", disconnect_handler, namespace)

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
                subscription_tasks = [
                    self.make_subscription_task(message, namespace)
                    for message in channel.subscribe.message.oneOf
                ]

                self._register_connection_handler(namespace, subscription_tasks)

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
                callback=message.x_ack and (lambda *args, **kwargs: None),
            )

        return task

    def make_publish_handler(self, message: Message) -> Callable:
        if message.x_ack is not None:

            def handler(*args, **kwargs):
                return generate_fake_data_from_schema(
                    message.x_ack.args, self.custom_formats
                )

            return handler

        return lambda *args, **kwargs: None
