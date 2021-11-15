from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type

from svarog import forge
from svarog import register_forge
from svarog.types import Forge

from asynction.exceptions import UnsupportedSecurityScheme

GLOBAL_NAMESPACE = "/"

JSONMappingValue = Any
JSONMapping = Mapping[str, JSONMappingValue]
JSONSchema = JSONMapping


class HTTPAuthenticationScheme(Enum):
    """
    https://www.iana.org/assignments/http-authschemes/http-authschemes.xhtml
    """

    BASIC = "basic"
    DIGEST = "digest"
    BEARER = "bearer"


class OAuth2FlowType(Enum):
    """
    https://www.asyncapi.com/docs/specifications/v2.2.0#oauthFlowsObject
    """

    IMPLICIT = "implicit"
    PASSWORD = "password"
    CLIENT_CREDENTIALS = "clientCredentials"
    AUTHORIZATION_CODE = "authorizationCode"


@dataclass
class OAuth2Flow:
    """
    https://www.asyncapi.com/docs/specifications/v2.2.0#oauthFlowObject
    """

    scopes: Mapping[str, str]
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    refresh_url: Optional[str] = None

    @staticmethod
    def forge(
        type_: Type["OAuth2Flow"], data: JSONMapping, forge: Forge
    ) -> "OAuth2Flow":
        return type_(
            scopes=forge(type_.__annotations__["scopes"], data.get("scopes")),
            authorization_url=forge(
                type_.__annotations__["authorization_url"], data.get("authorizationUrl")
            ),
            token_url=forge(type_.__annotations__["token_url"], data.get("tokenUrl")),
            refresh_url=forge(
                type_.__annotations__["refresh_url"], data.get("refreshUrl")
            ),
        )


register_forge(OAuth2Flow, OAuth2Flow.forge)


class SecuritySchemesType(Enum):
    """
    https://www.asyncapi.com/docs/specifications/v2.2.0#securitySchemeObjectType
    """

    USER_PASSWORD = "userPassword"
    API_KEY = "apiKey"
    X509 = "X509"
    SYMMETRIC_ENCRYPTION = "symmetricEncryption"
    ASYMMETRIC_ENCRYPTION = "asymmetricEncryption"
    HTTP_API_KEY = "httpApiKey"
    HTTP = "http"
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openIdConnect"
    PLAIN = "plain"
    SCRAM_SHA256 = "scramSha256"
    SCRAM_SHA512 = "scramSha512"
    GSSAPI = "gssapi"


SUPPORTED_SECURITY_SCHEMES = frozenset(
    [
        SecuritySchemesType.HTTP,
        SecuritySchemesType.HTTP_API_KEY,
        SecuritySchemesType.OAUTH2,
    ]
)
SUPPORTED_HTTP_AUTHENTICATION_SCHEMES = frozenset(
    [HTTPAuthenticationScheme.BASIC, HTTPAuthenticationScheme.BEARER]
)


@dataclass
class SecurityScheme:
    """
    https://www.asyncapi.com/docs/specifications/v2.2.0#securitySchemeObject
    """

    type: SecuritySchemesType
    description: Optional[str] = None
    name: Optional[str] = None  # Required for httpApiKey
    in_: Optional[str] = None  # Required for httpApiKey | apiKey
    scheme: Optional[HTTPAuthenticationScheme] = None  # Required for http
    bearer_format: Optional[str] = None  # Optional for http ("bearer")
    flows: Optional[Mapping[OAuth2FlowType, OAuth2Flow]] = None  # Required for oauth2
    open_id_connect_url: Optional[str] = None  # Required for openIdConnect

    x_basic_info_func: Optional[str] = None  # Required for http(basic)
    x_token_info_func: Optional[str] = None  # Required for oauth2
    x_api_key_info_func: Optional[str] = None  # Required for apiKey
    x_scope_validate_func: Optional[str] = None  # Optional for oauth2

    def __post_init__(self):
        if self.type not in SUPPORTED_SECURITY_SCHEMES:
            raise UnsupportedSecurityScheme(self.type)

        if self.type == SecuritySchemesType.HTTP:
            if not self.scheme:
                raise
            if self.scheme not in SUPPORTED_HTTP_AUTHENTICATION_SCHEMES:
                raise

    @staticmethod
    def forge(
        type_: Type["SecurityScheme"], data: JSONMapping, forge: Forge
    ) -> "SecurityScheme":
        return type_(
            type=forge(type_.__annotations__["type"], data.get("type")),
            description=forge(
                type_.__annotations__["description"], data.get("description")
            ),
            name=forge(type_.__annotations__["name"], data.get("name")),
            in_=forge(type_.__annotations__["in_"], data.get("in")),
            scheme=forge(type_.__annotations__["scheme"], data.get("scheme")),
            bearer_format=forge(
                type_.__annotations__["bearer_format"], data.get("bearerFormat")
            ),
            flows=forge(type_.__annotations__["flows"], data.get("flows")),
            open_id_connect_url=forge(
                type_.__annotations__["open_id_connect_url"],
                data.get("openIdConnectUrl"),
            ),
            x_basic_info_func=forge(
                type_.__annotations__["x_basic_info_func"], data.get("x-basicInfoFunc")
            ),
            x_token_info_func=forge(
                type_.__annotations__["x_token_info_func"], data.get("x-tokenInfoFunc")
            ),
            x_api_key_info_func=forge(
                type_.__annotations__["x_api_key_info_func"],
                data.get("x-apiKeyInfoFunc"),
            ),
            x_scope_validate_func=forge(
                type_.__annotations__["x_scope_validate_func"],
                data.get("x-scopeValidateFunc"),
            ),
        )


register_forge(SecurityScheme, SecurityScheme.forge)


@dataclass
class SecurityRequirement:
    # https://www.asyncapi.com/docs/specifications/v2.2.0#securityRequirementObject
    name: str
    scopes: Sequence[str]

    @staticmethod
    def forge(
        type_: Type["SecurityRequirement"], data: JSONMapping, forge: Forge
    ) -> "SecurityRequirement":
        # Since the API file technically is a list of objects in the form
        # name: [scopes]
        # we have to make sure that the object doesn't actually have more
        # keys for some reason. If it does it is malformed
        if len(data) > 1:
            print(data)
            raise ValueError

        # now that we are sure the object is well formed
        # we take the first (and only) key value pair as name: scopes
        name, scopes = next(iter(data.items()))
        return type_(
            name=forge(type_.__annotations__["name"], name),
            scopes=forge(type_.__annotations__["scopes"], scopes),
        )


register_forge(SecurityRequirement, SecurityRequirement.forge)


@dataclass
class MessageAck:
    """The specification of a message acknowledgement"""

    args: JSONSchema


@dataclass
class Message:
    """
    https://www.asyncapi.com/docs/specifications/2.2.0#messageObject

    The above message object is extended as follows:
    * `x-handler`: Allows the coupling of the message specification to
    an event handler (which is a python callable). It SHOULD only be used
    for messages under a `publish` operation. Deserialized to `x_handler`.
    * `x-ack`: The specification of the acknowledgement packet that the message receiver
    transmits to the message sender. The acknowledgement args are passed as an input
    to the callback of the `emit`/`send` function. Deserialized to `x_ack`.

    The extentions are implemented as per:
    https://www.asyncapi.com/docs/specifications/2.2.0#specificationExtensions
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
    """https://www.asyncapi.com/docs/specifications/2.2.0#operationObject"""

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
    """https://www.asyncapi.com/docs/specifications/2.2.0#channelBindingsObject"""

    ws: WebSocketsChannelBindings


@dataclass
class ChannelHandlers:
    connect: Optional[str] = None
    disconnect: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Channel:
    """
    https://www.asyncapi.com/docs/specifications/2.2.0#channelItemObject

    The above channel item object is extended to
    support default namespace handlers as per:
    https://www.asyncapi.com/docs/specifications/2.2.0#specificationExtensions

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


class ServerProtocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    WS = "ws"
    WSS = "wss"


@dataclass
class Server:
    """https://www.asyncapi.com/docs/specifications/2.2.0#serverObject"""

    url: str
    protocol: ServerProtocol
    security: Optional[Sequence[SecurityRequirement]] = None


@dataclass
class Info:
    """https://www.asyncapi.com/docs/specifications/v2.2.0#infoObject"""

    title: str
    version: str
    description: Optional[str] = None


@dataclass
class Components:
    """https://www.asyncapi.com/docs/specifications/v2.2.0#componentsObject"""

    security_schemes: Optional[Mapping[str, SecurityScheme]] = None

    @staticmethod
    def forge(
        type_: Type["Components"], data: JSONMapping, forge: Forge
    ) -> "Components":
        return type_(
            security_schemes=forge(
                type_.__annotations__["security_schemes"], data.get("securitySchemes")
            )
        )


register_forge(Components, Components.forge)


@dataclass
class AsyncApiSpec:
    """https://www.asyncapi.com/docs/specifications/2.2.0#A2SObject"""

    asyncapi: str
    channels: Mapping[str, Channel]
    info: Info
    servers: Mapping[str, Server] = field(default_factory=dict)
    components: Components = field(default_factory=Components)

    @staticmethod
    def from_dict(data: JSONMapping) -> "AsyncApiSpec":
        spec = forge(AsyncApiSpec, data)
        spec._raw = data  # type: ignore
        return spec

    def to_dict(self) -> JSONMapping:
        return getattr(self, "_raw", asdict(self))


ErrorHandler = Callable[[Exception], None]
