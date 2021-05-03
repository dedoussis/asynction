from dataclasses import dataclass
from dataclasses import replace
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type

from svarog import forge
from svarog import register_forge
from svarog.types import Forge

JSONMappingValue = Any
JSONMapping = Mapping[str, JSONMappingValue]
JSONSchema = JSONMapping

GLOBAL_NAMESPACE = "/"


@dataclass
class Message:
    """
    https://www.asyncapi.com/docs/specifications/2.0.0#messageObject

    The above message object is extended to enable the coupling
    of the message spec to an event handler (with is a python callable).
    The extention is implemented as per:
    https://www.asyncapi.com/docs/specifications/2.0.0#specificationExtensions

    The `x_handler` field is serialized as `x-handler`.
    """

    name: str
    payload: Optional[JSONSchema] = None
    x_handler: Optional[str] = None

    @staticmethod
    def forge(type_: Type["Message"], data: JSONMapping, forge: Forge) -> "Message":
        forged = type_(
            payload=forge(type_.__annotations__["payload"], data["payload"]),
            name=forge(type_.__annotations__["name"], data["name"]),
        )

        x_handler_data = data.get("x-handler")

        if x_handler_data is None:
            return forged

        return replace(
            forged,
            x_handler=forge(type_.__annotations__["x_handler"], x_handler_data),
        )


register_forge(Message, Message.forge)


@dataclass
class OneOfMessages:
    """Using `oneOf` to specify multiple messages per operation"""

    oneOf: Sequence[Message]

    @staticmethod
    def forge(
        type_: Type["OneOfMessages"], data: JSONMapping, forge: Forge
    ) -> "OneOfMessages":
        if "oneOf" in data:
            return type_(
                oneOf=forge(type_.__annotations__["oneOf"], data["oneOf"]),
            )

        return type_(oneOf=[forge(Message, data)])

    def with_name(self, name: str) -> Optional[Message]:
        for message in self.oneOf:
            if message.name == name:
                return message

        return None


register_forge(OneOfMessages, OneOfMessages.forge)


@dataclass
class Operation:
    """https://www.asyncapi.com/docs/specifications/2.0.0#operationObject"""

    message: OneOfMessages


@dataclass
class WebSocketsChannelBindings:
    """
    https://github.com/asyncapi/bindings/tree/master/websockets#channel-binding-object
    """

    method: Optional[str] = None
    query: Optional[JSONSchema] = None
    headers: Optional[JSONSchema] = None  # TODO: Convert header properties to lowercase
    bindingVersion: str = "latest"


@dataclass
class ChannelBindings:
    """https://www.asyncapi.com/docs/specifications/2.0.0#channelBindingsObject"""

    ws: WebSocketsChannelBindings


@dataclass
class ChannelHandlers:
    connect: Optional[str] = None
    disconnect: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Channel:
    """
    https://www.asyncapi.com/docs/specifications/2.0.0#channelItemObject

    The above channel item object is extended to
    support default namespace handlers as per:
    https://www.asyncapi.com/docs/specifications/2.0.0#specificationExtensions

    The `x_handlers` field is serialized as `x-handlers`.
    """

    subscribe: Optional[Operation] = None
    publish: Optional[Operation] = None
    bindings: Optional[ChannelBindings] = None
    x_handlers: Optional[ChannelHandlers] = None

    def __post_init__(self):
        if self.publish is not None:
            for message in self.publish.message.oneOf:
                if message.x_handler is None:
                    raise ValueError(
                        f"Message {message.name} is missing the x-handler attribute.\n"
                        "Every message under a publish operation "
                        "should have a handler defined."
                    )

    @staticmethod
    def forge(type_: Type["Channel"], data: JSONMapping, forge: Forge) -> "Channel":
        forged = type_(
            subscribe=forge(type_.__annotations__["subscribe"], data.get("subscribe")),
            publish=forge(type_.__annotations__["publish"], data.get("publish")),
            bindings=forge(type_.__annotations__["bindings"], data.get("bindings")),
        )

        x_handlers_data = data.get("x-handlers")

        if x_handlers_data is None:
            return forged

        return replace(
            forged,
            x_handlers=forge(type_.__annotations__["x_handlers"], x_handlers_data),
        )


register_forge(Channel, Channel.forge)


@dataclass
class AsyncApiSpec:
    """https://www.asyncapi.com/docs/specifications/2.0.0#A2SObject"""

    channels: Mapping[str, Channel]

    @staticmethod
    def from_dict(data: JSONMapping) -> "AsyncApiSpec":
        return forge(AsyncApiSpec, data)
