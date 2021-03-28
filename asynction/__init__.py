from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from importlib import import_module
from pathlib import Path
from pathlib import PurePath
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Type

import yaml
from flask import Flask
from flask_socketio import SocketIO
from jsonschema import RefResolver
from svarog import forge
from svarog import register_forge
from svarog.types import Forge

JSONMappingValue = Any
JSONMapping = Mapping[str, JSONMappingValue]
JSONSchema = JSONMapping

MAIN_NAMESPACE = "/"


@dataclass
class Message:
    """https://www.asyncapi.com/docs/specifications/2.0.0#messageObject"""

    payload: JSONSchema


@dataclass
class Namespace:
    """SocketIO specific object: https://socket.io/docs/v4/namespaces/
    Referenced in the `x-namespaces` extention of the specification.
    """

    description: Optional[str] = None
    errorHandler: Optional[str] = None


DEFAULT_NAMESPACES = {MAIN_NAMESPACE: Namespace(description="Main namespace")}


@dataclass
class Operation:
    """https://www.asyncapi.com/docs/specifications/2.0.0#operationObject"""

    message: Message
    operationId: Optional[str] = None


@dataclass
class Channel:
    """https://www.asyncapi.com/docs/specifications/2.0.0#channelItemObject"""

    subscribe: Optional[Operation] = None
    publish: Optional[Operation] = None

    def __post_init__(self):
        if self.subscribe is not None and self.subscribe.operationId is None:
            raise ValueError("operationId is required for subsbribe operations.")


@dataclass
class AsyncApiSpec:
    """
    https://www.asyncapi.com/docs/specifications/2.0.0#A2SObject

    The above A2S object is extended to support SocketIO namespaces as per:
    https://www.asyncapi.com/docs/specifications/2.0.0#specificationExtensions

    The `x_namespaces` field is serialized as `x-namespaces`.
    """

    channels: Mapping[str, Channel]
    x_namespaces: Mapping[str, Namespace] = field(
        default_factory=lambda: DEFAULT_NAMESPACES
    )


def forge_namespace_extended(type_: Type, data: JSONMapping, forge: Forge):
    typed_kwargs: Mapping[str, Any] = {}
    for field_ in fields(type_):
        field_data = (
            data.get("x-namespaces")
            if field_.name == "x_namespaces"
            else data.get(field_.name)
        )
        if field_data is not None:
            typed_kwargs = {**typed_kwargs, field_.name: forge(field_.type, field_data)}

    return type_(**typed_kwargs)


register_forge(AsyncApiSpec, forge_namespace_extended)


def resolve_references(raw_spec: JSONMapping) -> JSONMapping:
    resolver = RefResolver.from_schema(raw_spec)

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
            else:
                return k, v

        return dict(map(transform, unresolved.items()))

    return deep_resolve(raw_spec)


def load_spec(spec_path: Path) -> AsyncApiSpec:
    with open(spec_path) as f:
        serialized = f.read()
        raw = yaml.safe_load(serialized)

    raw_resolved = resolve_references(raw_spec=raw)

    return forge(AsyncApiSpec, raw_resolved)


def decompose_channel_path(channel_path: str) -> Tuple[str, Optional[str]]:
    pp = PurePath(channel_path if channel_path.startswith("/") else f"/{channel_path}")
    return pp.name, None if not pp.parent.name else str(pp.parent)


def load_handler(handler_id: str) -> Callable[..., None]:
    *module_path_elements, object_name = handler_id.split(".")
    module = import_module(".".join(module_path_elements))

    return getattr(module, object_name)


def register_event_handlers(server: SocketIO, spec: AsyncApiSpec) -> None:
    for channel_path, channel in spec.channels.items():
        if channel.subscribe is not None:
            channel_name, namespace = decompose_channel_path(channel_path)
            if namespace is not None and namespace not in spec.x_namespaces:
                raise ValueError(
                    f"Namespace {namespace} is not defined in x-namespaces."
                )
            assert channel.subscribe.operationId is not None
            handler = load_handler(channel.subscribe.operationId)
            server.on_event(channel_name, handler, namespace)


def register_error_handlers(server: SocketIO, spec: AsyncApiSpec) -> None:
    for ns_name, ns_definition in spec.x_namespaces.items():
        if ns_definition.errorHandler is None:
            continue

        exc_handler = load_handler(ns_definition.errorHandler)

        if ns_name == MAIN_NAMESPACE:
            server.on_error_default(exc_handler)
        else:
            server.on_error(ns_name)(exc_handler)


class AsynctionSocketIO(SocketIO):
    @classmethod
    def from_spec(
        cls, spec_path: Path, app: Optional[Flask] = None, **kwargs
    ) -> SocketIO:
        sio = cls(app, **kwargs)
        spec = load_spec(spec_path=spec_path)
        register_event_handlers(server=sio, spec=spec)
        register_error_handlers(server=sio, spec=spec)
        return sio
