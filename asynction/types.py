from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
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
class MessageAck:
    """The specification of a message acknowledgement"""

    args: JSONSchema


@dataclass
class Message:
    """
    https://www.asyncapi.com/docs/specifications/2.0.0#messageObject

    The above message object is extended as follows:
    * `x-handler`: Allows the coupling of the message specification to
    an event handler (which is a python callable). It SHOULD only be used
    for messages under a `publish` operation. Deserialized to `x_handler`.
    * `x-ack`: The specification of the acknowledgement packet that the message receiver
    transmits to the message sender. The acknowledgement args are passed as an input
    to the callback of the `emit`/`send` function. Deserialized to `x_ack`.

    The extentions are implemented as per:
    https://www.asyncapi.com/docs/specifications/2.0.0#specificationExtensions
    """

    name: str
    payload: Optional[JSONSchema] = None
    x_handler: Optional[str] = None
    x_ack: Optional[MessageAck] = None

    @staticmethod
    def forge(type_: Type["Message"], data: JSONMapping, forge: Forge) -> "Message":
        return type_(
            name=forge(type_.__annotations__["name"], data["name"]),
            payload=forge(type_.__annotations__["payload"], data.get("payload")),
            x_handler=forge(type_.__annotations__["x_handler"], data.get("x-handler")),
            x_ack=forge(type_.__annotations__["x_ack"], data.get("x-ack")),
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
        return type_(
            subscribe=forge(type_.__annotations__["subscribe"], data.get("subscribe")),
            publish=forge(type_.__annotations__["publish"], data.get("publish")),
            bindings=forge(type_.__annotations__["bindings"], data.get("bindings")),
            x_handlers=forge(
                type_.__annotations__["x_handlers"], data.get("x-handlers")
            ),
        )


register_forge(Channel, Channel.forge)


@dataclass
class Server:
    """https://www.asyncapi.com/docs/specifications/2.0.0#serverObject"""

    url: str


@dataclass
class AsyncApiSpec:
    """https://www.asyncapi.com/docs/specifications/2.0.0#A2SObject"""

    channels: Mapping[str, Channel]
    servers: Mapping[str, Server] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: JSONMapping) -> "AsyncApiSpec":
        return forge(AsyncApiSpec, data)


ErrorHandler = Callable[[Exception], None]
