from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from pathlib import PurePath
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Type

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

    @staticmethod
    def from_dict(data: JSONMapping) -> "AsyncApiSpec":
        return forge(AsyncApiSpec, data)


register_forge(AsyncApiSpec, AsyncApiSpec.forge)
