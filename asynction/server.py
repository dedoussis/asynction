"""
The ``AsynctionSocketIO`` server is essentially a flask_socketio.SocketIO server
with an additional factory classmethod.
"""

from functools import singledispatch
from importlib import import_module
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Optional
from typing import Sequence

import jsonschema
import yaml
from flask import Flask
from flask_socketio import SocketIO

from asynction.exceptions import ValidationException
from asynction.types import GLOBAL_NAMESPACE
from asynction.types import AsyncApiSpec
from asynction.types import ChannelBindings
from asynction.types import ChannelHandlers
from asynction.types import ErrorHandler
from asynction.types import JSONMapping
from asynction.validation import bindings_validator_factory
from asynction.validation import callback_validator_factory
from asynction.validation import publish_message_validator_factory
from asynction.validation import validate_payload


@singledispatch
def deep_resolve(unresovled: Any, resolver: jsonschema.RefResolver) -> Any:
    return unresovled


@deep_resolve.register(dict)
def _deep_resolve_mapping(
    unresolved: JSONMapping, resolver: jsonschema.RefResolver
) -> JSONMapping:
    return {
        k: deep_resolve(resolver.resolve(v["$ref"])[-1] if "$ref" in v else v, resolver)
        for k, v in unresolved.items()
    }


@deep_resolve.register(list)
@deep_resolve.register(tuple)
@deep_resolve.register(set)
def _deep_resolve_sequence(
    unresolved: Sequence, resolver: jsonschema.RefResolver
) -> Sequence:
    return unresolved.__class__(  # type: ignore
        [
            deep_resolve(
                resolver.resolve(item["$ref"])[-1] if "$ref" in item else item, resolver
            )
            for item in unresolved
        ]
    )


def resolve_references(raw_spec: JSONMapping) -> JSONMapping:
    resolver = jsonschema.RefResolver.from_schema(raw_spec)
    return deep_resolve(raw_spec, resolver)


def load_spec(spec_path: Path) -> AsyncApiSpec:
    with open(spec_path) as f:
        serialized = f.read()
        raw = yaml.safe_load(serialized)

    raw_resolved = resolve_references(raw_spec=raw)

    return AsyncApiSpec.from_dict(raw_resolved)


def load_handler(handler_id: str) -> Callable:
    *module_path_elements, object_name = handler_id.split(".")
    module = import_module(".".join(module_path_elements))

    return getattr(module, object_name)


class AsynctionSocketIO(SocketIO):
    def __init__(
        self,
        spec: AsyncApiSpec,
        validation: bool = True,
        app: Optional[Flask] = None,
        **kwargs,
    ):
        """This is a private constructor.
        Use the ``AsynctionSocketIO.from_spec`` factory instead.
        """
        super().__init__(app=app, **kwargs)
        self.spec = spec
        self.validation = validation

    @classmethod
    def from_spec(
        cls,
        spec_path: Path,
        validation: bool = True,
        server_name: Optional[str] = None,
        default_error_handler: Optional[ErrorHandler] = None,
        app: Optional[Flask] = None,
        **kwargs,
    ) -> SocketIO:
        """Create a Flask-SocketIO server from an AsyncAPI spec.
        This is the single entrypoint to the Asynction API.

        :param spec_path: The path where the AsyncAPI YAML specification is located.
        :param validation: When set to ``False``, message payloads and channel
                           bindings are NOT validated. Defaults to ``True``.
        :param server_name: The server to pick from the Async API ``servers`` object.
                            The server object is then used to configure
                            the path ``kwarg`` of the SocketIO server.
        :param default_error_handler: The error handler that handles any namespace
                                      without an explicit error handler.
                                      Equivelant of ``@socketio.on_error_default``
        :param app: The flask application instance. Defaults to ``None``.
        :param kwargs: Flask-SocketIO, Socket.IO and Engine.IO server options.

        :returns: A Flask-SocketIO server.
                  The server has all the event and error handlers registered.

        Example::

            asio = AsynctionSocketIO.from_spec(
                spec_path="./docs/asyncapi.yaml",
                app=flask_app,
                message_queue="redis://localhost:6379",
                # any other kwarg that the flask_socketio.SocketIO constructor accepts
            )

        """
        spec = load_spec(spec_path=spec_path)

        if (
            server_name is not None
            and kwargs.get("path") is None
            and kwargs.get("resource") is None
        ):
            server = spec.servers.get(server_name)
            if server is None:
                raise ValueError(f"Server {server_name} is not defined in the spec.")
            host_length = len(server.url.split("/")[0])
            server_path = server.url[host_length:]
            if server_path:
                kwargs["path"] = server_path

        asio = cls(spec, validation, app, **kwargs)
        asio._register_handlers(default_error_handler)
        return asio

    def _register_namespace_handlers(
        self,
        namespace: str,
        channel_handlers: ChannelHandlers,
        channel_bindings: Optional[ChannelBindings],
    ) -> None:
        if channel_handlers.connect is not None:
            handler = load_handler(channel_handlers.connect)

            if self.validation:
                with_bindings_validation = bindings_validator_factory(channel_bindings)
                handler = with_bindings_validation(handler)

            self.on_event("connect", handler, namespace)

        if channel_handlers.disconnect is not None:
            handler = load_handler(channel_handlers.disconnect)
            self.on_event("disconnect", handler, namespace)

        if channel_handlers.error is not None:
            handler = load_handler(channel_handlers.error)
            self.on_error(namespace)(handler)

    def _register_handlers(
        self, default_error_handler: Optional[ErrorHandler] = None
    ) -> None:
        for namespace, channel in self.spec.channels.items():
            if channel.publish is not None:
                for message in channel.publish.message.oneOf:
                    assert message.x_handler is not None
                    handler = load_handler(message.x_handler)

                    if self.validation:
                        with_payload_validation = publish_message_validator_factory(
                            message=message
                        )
                        handler = with_payload_validation(handler)

                    self.on_event(message.name, handler, namespace)

            if channel.x_handlers is not None:
                self._register_namespace_handlers(
                    namespace, channel.x_handlers, channel.bindings
                )

        if default_error_handler is not None:
            self.on_error_default(default_error_handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        if self.validation:
            namespace = kwargs.get("namespace", GLOBAL_NAMESPACE)
            channel = self.spec.channels.get(namespace)

            if channel is None:
                raise ValidationException(
                    f"Failed to emit because the {namespace} "
                    "namespace is not defined in the API spec."
                )

            if channel.subscribe is None:
                raise ValidationException(
                    f"Failed to emit because the {namespace} namespace "
                    "does not have any subscribe operations defined."
                )

            message = channel.subscribe.message.with_name(event)
            if message is None:
                raise ValidationException(
                    f"Event {event} is not registered under the {namespace} namespace"
                )

            validate_payload(args, message.payload)

            callback = kwargs.get("callback")
            if callback is not None:
                with_validation = callback_validator_factory(message=message)
                kwargs["callback"] = with_validation(callback)

        return super().emit(event, *args, **kwargs)
