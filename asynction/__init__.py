from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from pathlib import PurePath
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Optional
from typing import Tuple

import yaml
from flask import Flask
from flask_socketio import SocketIO
from jsonschema import RefResolver
from svarog import forge

JSONMappingValue = Any
JSONMapping = Mapping[str, JSONMappingValue]
JSONSchema = JSONMapping


@dataclass
class Message:
    """https://www.asyncapi.com/docs/specifications/2.0.0#messageObject"""

    payload: JSONSchema


@dataclass
class Operation:
    """https://www.asyncapi.com/docs/specifications/2.0.0#operationObject"""

    operationId: str
    message: Message


@dataclass
class Channel:
    """https://www.asyncapi.com/docs/specifications/2.0.0#channelItemObject"""

    subscribe: Optional[Operation] = None
    publish: Optional[Operation] = None


@dataclass
class AsyncApiSpec:
    """https://www.asyncapi.com/docs/specifications/2.0.0#A2SObject"""

    channels: Mapping[str, Channel]


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


def load_operation_handler(operation_id: str) -> Callable[..., None]:
    *module_path_elements, object_name = operation_id.split(".")
    module = import_module(".".join(module_path_elements))

    return getattr(module, object_name)


class AsynctionSocketIO(SocketIO):
    @classmethod
    def from_spec(
        cls, spec_path: Path, app: Optional[Flask] = None, **kwargs
    ) -> SocketIO:
        sio = cls(app, **kwargs)
        spec = load_spec(spec_path=spec_path)

        for channel_path, channel in spec.channels.items():
            channel_name, namespace = decompose_channel_path(channel_path)
            if channel.subscribe is not None:
                handler = load_operation_handler(channel.subscribe.operationId)
                sio.on_event(channel_name, handler, namespace)

        return sio
