from importlib import import_module
from pathlib import Path
from typing import Callable
from typing import Optional
from typing import Tuple

import jsonschema
import yaml
from flask import Flask
from flask_socketio import SocketIO

from asynction.types import GLOBAL_NAMESPACE
from asynction.types import AsyncApiSpec
from asynction.types import ChannelHandlers
from asynction.types import JSONMapping
from asynction.types import JSONMappingValue
from asynction.validation import payload_validator_factory
from asynction.validation import validate_payload


def resolve_references(raw_spec: JSONMapping) -> JSONMapping:
    resolver = jsonschema.RefResolver.from_schema(raw_spec)

    def deep_resolve(unresolved: JSONMapping) -> JSONMapping:
        def transform(
            item: Tuple[str, JSONMappingValue]
        ) -> Tuple[str, JSONMappingValue]:
            k, v = item
            if isinstance(v, dict):
                resolved_v = (
                    resolver.resolve(v["$ref"])[-1] if "$ref" in v else deep_resolve(v)
                )
                return k, resolved_v
            if isinstance(v, (list, tuple, set)):
                resolved_v = v.__class__(
                    [
                        resolver.resolve(item["$ref"])[-1]
                        if "$ref" in item
                        else deep_resolve(item)
                        for item in v
                    ]
                )
                return k, resolved_v
            else:
                return k, v

        return dict(map(transform, unresolved.items()))

    return deep_resolve(raw_spec)


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
        super().__init__(app=app, **kwargs)
        self.spec = spec
        self.validation = validation

    @classmethod
    def from_spec(
        cls,
        spec_path: Path,
        validation: bool = True,
        app: Optional[Flask] = None,
        **kwargs,
    ) -> SocketIO:
        spec = load_spec(spec_path=spec_path)
        asio = cls(spec, validation, app, **kwargs)
        asio._register_handlers()
        return asio

    def _register_namespace_handlers(
        self, namespace: str, channel_handlers: ChannelHandlers
    ) -> None:
        if channel_handlers.connect is not None:
            handler = load_handler(channel_handlers.connect)
            self.on_event("connect", handler, namespace)

        if channel_handlers.disconnect is not None:
            handler = load_handler(channel_handlers.disconnect)
            self.on_event("disconnect", handler, namespace)

        if channel_handlers.error is not None:
            handler = load_handler(channel_handlers.error)
            if namespace == GLOBAL_NAMESPACE:
                self.on_error_default(handler)
            else:
                self.on_error(namespace)(handler)

    def _register_handlers(self) -> None:
        for namespace, channel in self.spec.channels.items():
            if channel.publish is not None:
                for message in channel.publish.message.oneOf:
                    assert message.x_handler is not None
                    handler = load_handler(message.x_handler)

                    if self.validation:
                        with_payload_validation = payload_validator_factory(
                            schema=message.payload
                        )
                        handler = with_payload_validation(handler)

                    self.on_event(message.name, handler, namespace)

            if channel.x_handlers is not None:
                self._register_namespace_handlers(namespace, channel.x_handlers)

    def emit(self, event: str, *args, **kwargs) -> None:
        if self.validation:
            namespace = kwargs.get("namespace", GLOBAL_NAMESPACE)
            channel = self.spec.channels.get(namespace)

            if channel is None:
                raise RuntimeError(
                    f"Failed to emit because the {namespace} "
                    "namespace is not defined in the API spec."
                )

            if channel.subscribe is None:
                raise RuntimeError(
                    f"Failed to emit because {namespace} does not"
                    " have any subscribe operation defined."
                )

            message = channel.subscribe.message.with_name(event)
            if message is None:
                raise RuntimeError(
                    f"Event {event} is not registered under namespace {namespace}"
                )

            validate_payload(args, message.payload)

        return super().emit(event, *args, **kwargs)
