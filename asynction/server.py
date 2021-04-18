from importlib import import_module
from pathlib import Path
from typing import Callable
from typing import Optional
from typing import Tuple

import jsonschema
import yaml
from flask import Flask
from flask_socketio import SocketIO

from asynction.types import MAIN_NAMESPACE
from asynction.types import AsyncApiSpec
from asynction.types import ChannelPath
from asynction.types import JSONMapping
from asynction.types import JSONMappingValue
from asynction.validation import validate_payload
from asynction.validation import validator_factory


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
