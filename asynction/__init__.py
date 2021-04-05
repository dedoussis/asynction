from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from functools import wraps
from importlib import import_module
from pathlib import Path
from pathlib import PurePath
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type

import jsonschema
import yaml
from flask import Flask
from flask_socketio import SocketIO
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

    message: Optional[Message] = None
    operationId: Optional[str] = None


@dataclass
class Channel:
    """https://www.asyncapi.com/docs/specifications/2.0.0#channelItemObject"""

    subscribe: Optional[Operation] = None
    publish: Optional[Operation] = None

    def __post_init__(self):
        if self.publish is not None and self.publish.operationId is None:
            raise ValueError("operationId is required for publish operations.")


@dataclass(frozen=True)
class ChannelPath:
    """
    Ιmplements the event handler namespacing semantic.
    This added semantic allows the registration
    of an event handler or a message validator
    under a particular namespace.
    """

    event_name: str
    namespace: str = MAIN_NAMESPACE

    @staticmethod
    def forge(type_: Type["ChannelPath"], data: str, _: Any) -> "ChannelPath":
        pp = PurePath(data if data.startswith("/") else f"/{data}")
        cp = type_(event_name=pp.name)
        if pp.parent.name:
            return replace(cp, namespace=str(pp.parent))

        return cp


register_forge(ChannelPath, ChannelPath.forge)


@dataclass
class AsyncApiSpec:
    """
    https://www.asyncapi.com/docs/specifications/2.0.0#A2SObject

    The above A2S object is extended to support SocketIO namespaces as per:
    https://www.asyncapi.com/docs/specifications/2.0.0#specificationExtensions

    The `x_namespaces` field is serialized as `x-namespaces`.
    """

    channels: Mapping[ChannelPath, Channel]
    x_namespaces: Mapping[str, Namespace] = field(
        default_factory=lambda: DEFAULT_NAMESPACES
    )

    @staticmethod
    def forge(
        type_: Type["AsyncApiSpec"], data: JSONMapping, forge: Forge
    ) -> "AsyncApiSpec":
        forged = type_(
            channels=forge(type_.__annotations__["channels"], data["channels"])
        )
        x_namespaces_data = data.get("x-namespaces")

        if x_namespaces_data is None:
            return forged

        return replace(
            forged,
            x_namespaces=forge(
                type_.__annotations__["x_namespaces"], x_namespaces_data
            ),
        )


register_forge(AsyncApiSpec, AsyncApiSpec.forge)


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


def load_handler(handler_id: str) -> Callable:
    *module_path_elements, object_name = handler_id.split(".")
    module = import_module(".".join(module_path_elements))

    return getattr(module, object_name)


def validate_payload(args: Sequence, operation: Operation) -> None:
    if operation.message is None or operation.message.payload is None:
        if args:
            raise RuntimeError(
                "Args provided for operation that has no message payload defined."
            )
        # No validation needed since no message is expected
        # and no args have been provided.
        return

    schema = operation.message.payload
    schema_type = schema["type"]
    if schema_type == "array":
        jsonschema.validate(args, schema)
    else:
        if len(args) > 1:
            raise RuntimeError(
                "Multiple handler arguments provided, "
                f"although schema type is: {schema_type}"
            )
        jsonschema.validate(args[0], schema)


def validator_factory(operation: Operation) -> Callable:
    def decorator(handler: Callable):
        @wraps(handler)
        def handler_with_validation(*args):
            validate_payload(args, operation)
            return handler(*args)

        return handler_with_validation

    return decorator


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
        asio._register_event_handlers()
        asio._register_error_handlers()
        return asio

    def _register_event_handlers(self) -> None:
        for cp, channel in self.spec.channels.items():
            if channel.publish is not None:
                if (
                    cp.namespace is not None
                    and cp.namespace not in self.spec.x_namespaces
                ):
                    raise ValueError(
                        f"Namespace {cp.namespace} is not defined in x-namespaces."
                    )

                assert channel.publish.operationId is not None
                handler = load_handler(channel.publish.operationId)

                if self.validation:
                    with_validation = validator_factory(operation=channel.publish)
                    handler = with_validation(handler)

                self.on_event(cp.event_name, handler, cp.namespace)

    def _register_error_handlers(self) -> None:
        for ns_name, ns_definition in self.spec.x_namespaces.items():
            if ns_definition.errorHandler is None:
                continue

            exc_handler = load_handler(ns_definition.errorHandler)

            if ns_name == MAIN_NAMESPACE:
                self.on_error_default(exc_handler)
            else:
                self.on_error(ns_name)(exc_handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        if self.validation:
            cp = ChannelPath(
                event_name=event, namespace=kwargs.get("namespace", MAIN_NAMESPACE)
            )
            channel = self.spec.channels.get(cp)

            if channel is None:
                raise RuntimeError(
                    f"Failed to emit because {cp} is not defined in the API spec."
                )

            if channel.subscribe is None:
                raise RuntimeError(
                    f"Failed to emit because {cp} does not"
                    " have a subscribe operation defined."
                )

            validate_payload(args, channel.subscribe)

        return super().emit(event, *args, **kwargs)
