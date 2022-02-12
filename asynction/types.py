from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from enum import Enum
from typing import Any
from typing import Callable
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type

from svarog import forge
from svarog import register_forge
from svarog.types import Forge

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
    https://www.asyncapi.com/docs/specifications/v2.3.0#oauthFlowsObject
    """

    IMPLICIT = "implicit"
    PASSWORD = "password"
    CLIENT_CREDENTIALS = "clientCredentials"
    AUTHORIZATION_CODE = "authorizationCode"


@dataclass
class OAuth2Flow:
    """
    https://www.asyncapi.com/docs/specifications/v2.3.0#oauthFlowObject
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


@dataclass
class OAuth2Flows:
    implicit: Optional[OAuth2Flow] = None
    password: Optional[OAuth2Flow] = None
    client_credentials: Optional[OAuth2Flow] = None
    authorization_code: Optional[OAuth2Flow] = None

    @staticmethod
    def forge(
        type_: Type["OAuth2Flows"], data: JSONMapping, forge: Forge
    ) -> "OAuth2Flows":
        return type_(
            implicit=forge(type_.__annotations__["implicit"], data.get("implicit")),
            password=forge(type_.__annotations__["password"], data.get("password")),
            client_credentials=forge(
                type_.__annotations__["client_credentials"],
                data.get("clientCredentials"),
            ),
            authorization_code=forge(
                type_.__annotations__["authorization_code"],
                data.get("authorizationCode"),
            ),
        )

    def __post_init__(self):
        if self.implicit is not None and self.implicit.authorization_url is None:
            raise ValueError("Implicit OAuth flow is missing Authorization URL")
        elif self.password is not None and self.password.token_url is None:
            raise ValueError("Password OAuth flow is missing Token URL")
        elif (
            self.client_credentials is not None
            and self.client_credentials.token_url is None
        ):
            raise ValueError("Client Credentials OAuth flow is missing Token URL")
        elif (
            self.authorization_code is not None
            and self.authorization_code.token_url is None
        ):
            raise ValueError("Authorization code OAuth flow is missing Token URL")

    def supported_scopes(self) -> Iterator[str]:
        for f in fields(self):
            flow = getattr(self, f.name)
            if flow:
                for scope in flow.scopes:
                    yield scope


register_forge(OAuth2Flows, OAuth2Flows.forge)


class SecuritySchemesType(Enum):
    """
    https://www.asyncapi.com/docs/specifications/v2.3.0#securitySchemeObjectType
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


class ApiKeyLocation(Enum):
    """
    https://www.asyncapi.com/docs/specifications/v2.3.0#securitySchemeObject
    """

    USER = "user"
    PASSWORD = "password"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"


@dataclass
class SecurityScheme:
    """
    https://www.asyncapi.com/docs/specifications/v2.3.0#securitySchemeObject
    """

    type: SecuritySchemesType
    description: Optional[str] = None
    name: Optional[str] = None  # Required for httpApiKey
    in_: Optional[ApiKeyLocation] = None  # Required for httpApiKey | apiKey
    scheme: Optional[HTTPAuthenticationScheme] = None  # Required for http
    bearer_format: Optional[str] = None  # Optional for http ("bearer")
    flows: Optional[OAuth2Flows] = None  # Required for oauth2
    open_id_connect_url: Optional[str] = None  # Required for openIdConnect

    x_basic_info_func: Optional[str] = None  # Required for http(basic)
    x_bearer_info_func: Optional[str] = None  # Required for http(bearer)
    x_token_info_func: Optional[str] = None  # Required for oauth2
    x_api_key_info_func: Optional[str] = None  # Required for apiKey
    x_scope_validate_func: Optional[str] = None  # Optional for oauth2

    def __post_init__(self):
        if not self.flows and self.type in [
            SecuritySchemesType.OAUTH2,
            SecuritySchemesType.OPENID_CONNECT,
        ]:
            raise ValueError(
                "flows field should be be defined " f"for {self.type} security schemes"
            )

        if self.type is SecuritySchemesType.HTTP:
            # NOTE bearer_format is optional for HTTP
            if not self.scheme:
                raise ValueError(f"scheme is required for {self.type} security schemes")

        if self.type is SecuritySchemesType.HTTP_API_KEY:
            options = [
                ApiKeyLocation.QUERY,
                ApiKeyLocation.HEADER,
                ApiKeyLocation.COOKIE,
            ]
            if not self.in_ or self.in_ not in options:
                raise ValueError(
                    f'"in" field must be one of {options} '
                    f"for {self.type} security schemes"
                )
            if not self.name:
                raise ValueError(f'"name" is required for {self.type} security schemes')

        # TODO include validation for other types

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
            x_bearer_info_func=forge(
                type_.__annotations__["x_bearer_info_func"],
                data.get("x-bearerInfoFunc"),
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


SecurityRequirement = Mapping[str, Sequence[str]]


@dataclass
class MessageAck:
    """The specification of a message acknowledgement"""

    args: JSONSchema


@dataclass
class Message:
    """
    https://www.asyncapi.com/docs/specifications/2.3.0#messageObject

    The above message object is extended as follows:
    * `x-handler`: Allows the coupling of the message specification to
    an event handler (which is a python callable). It SHOULD only be used
    for messages under a `publish` operation. Deserialized to `x_handler`.
    * `x-ack`: The specification of the acknowledgement packet that the message receiver
    transmits to the message sender. The acknowledgement args are passed as an input
    to the callback of the `emit`/`send` function. Deserialized to `x_ack`.

    The extentions are implemented as per:
    https://www.asyncapi.com/docs/specifications/2.3.0#specificationExtensions
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
    """https://www.asyncapi.com/docs/specifications/2.3.0#operationObject"""

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
    """https://www.asyncapi.com/docs/specifications/2.3.0#channelBindingsObject"""

    ws: WebSocketsChannelBindings


@dataclass
class ChannelHandlers:
    connect: Optional[str] = None
    disconnect: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Channel:
    """
    https://www.asyncapi.com/docs/specifications/2.3.0#channelItemObject

    The above channel item object is extended to
    support default namespace handlers as per:
    https://www.asyncapi.com/docs/specifications/2.3.0#specificationExtensions

    The `x_handlers` field is serialized as `x-handlers`.
    """

    subscribe: Optional[Operation] = None
    publish: Optional[Operation] = None
    bindings: Optional[ChannelBindings] = None
    x_handlers: Optional[ChannelHandlers] = None
    x_security: Optional[Sequence[SecurityRequirement]] = None

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
            x_security=forge(
                type_.__annotations__["x_security"], data.get("x-security")
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
    """https://www.asyncapi.com/docs/specifications/2.3.0#serverObject"""

    url: str
    protocol: ServerProtocol
    security: Sequence[SecurityRequirement] = field(default_factory=list)


@dataclass
class Info:
    """https://www.asyncapi.com/docs/specifications/v2.3.0#infoObject"""

    title: str
    version: str
    description: Optional[str] = None


@dataclass
class Components:
    """https://www.asyncapi.com/docs/specifications/v2.3.0#componentsObject"""

    security_schemes: Mapping[str, SecurityScheme] = field(default_factory=dict)

    @staticmethod
    def forge(
        type_: Type["Components"], data: JSONMapping, forge: Forge
    ) -> "Components":
        return type_(
            security_schemes=forge(
                type_.__annotations__["security_schemes"],
                data.get("securitySchemes", dict()),
            )
        )


register_forge(Components, Components.forge)


@dataclass
class AsyncApiSpec:
    """https://www.asyncapi.com/docs/specifications/2.3.0#A2SObject"""

    asyncapi: str
    channels: Mapping[str, Channel]
    info: Info
    servers: Mapping[str, Server] = field(default_factory=dict)
    components: Components = field(default_factory=Components)

    def __post_init__(self):
        for server_name, server in self.servers.items():
            for security_req in server.security:
                self._validate_security_requirement(security_req, server_name)

        for channel_name, channel in self.channels.items():
            if channel.x_security is not None:
                for security_req in channel.x_security:
                    self._validate_security_requirement(security_req, channel_name)

    def _validate_security_requirement(
        self, requirement: SecurityRequirement, required_by: str
    ) -> None:
        (security_scheme_name, scopes), *other = requirement.items()

        if other:
            raise ValueError(
                f"{required_by} contains invalid "
                f"security requirement: {requirement}"
            )

        security_scheme = self.components.security_schemes.get(security_scheme_name)
        if security_scheme is None:
            raise ValueError(
                f"{security_scheme_name} referenced within '{requirement}'"
                " server does not exist in components/securitySchemes"
            )

        if scopes:
            if security_scheme.type not in [
                SecuritySchemesType.OAUTH2,
                SecuritySchemesType.OPENID_CONNECT,
            ]:
                raise ValueError(
                    "Scopes MUST be an empty array for "
                    f"{security_scheme.type} security requirements"
                )

            if security_scheme.type is SecuritySchemesType.OAUTH2:
                if security_scheme.flows:
                    supported_scopes = security_scheme.flows.supported_scopes()

                    for scope in scopes:
                        if scope not in supported_scopes:
                            raise ValueError(
                                f"OAuth2 scope {scope} is not defined within "
                                f"the {security_scheme_name} security scheme"
                            )

    @staticmethod
    def from_dict(data: JSONMapping) -> "AsyncApiSpec":
        spec = forge(AsyncApiSpec, data)
        spec._raw = data  # type: ignore
        return spec

    def to_dict(self) -> JSONMapping:
        return getattr(self, "_raw", asdict(self))


ErrorHandler = Callable[[Exception], None]
