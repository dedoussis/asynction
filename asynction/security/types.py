from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Sequence, Type

from svarog import register_forge
from svarog.types import Forge

from asynction.common_types import JSONMapping
from .exceptions import UnsupportedSecurityScheme


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
        type_: Type["OAuth2Flow"],
        data: JSONMapping,
        forge: Forge
    ) -> "OAuth2Flow":
        return type_(
            scopes=forge(
                type_.__annotations__["scopes"],
                data.get("scopes")
            ),
            authorization_url=forge(
                type_.__annotations__["authorization_url"],
                data.get("authorizationUrl")
            ),
            token_url=forge(
                type_.__annotations__["token_url"],
                data.get("tokenUrl")
            ),
            refresh_url=forge(
                type_.__annotations__["refresh_url"],
                data.get("refreshUrl")
            )
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


@dataclass
class SecurityScheme:
    """
    https://www.asyncapi.com/docs/specifications/v2.2.0#securitySchemeObject
    """
    type: SecuritySchemeType
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

    @staticmethod
    def forge(
        type_: Type["SecurityScheme"],
        data: JSONMapping,
        forge: Forge
    ) -> "SecurityScheme":

        scheme_type_raw = data.get("type")
        if not scheme_type_raw:
            raise UnsupportedSecurityScheme
        try:
            SecuritySchemesType(scheme_type_raw)
        except ValueError:
            raise UnsupportedSecurityScheme(scheme_type_raw)

        return type_(
            type=forge(
                type_.__annotations__["type"],
                data.get("type")
            ),
            description=forge(
                type_.__annotations__["description"],
                data.get("description")
            ),
            name=forge(
                type_.__annotations__["name"],
                data.get("name")
            ),
            in_=forge(
                type_.__annotations__["in_"],
                data.get("in")
            ),
            scheme=forge(
                type_.__annotations__["scheme"],
                data.get("scheme")
            ),
            bearer_format=forge(
                type_.__annotations__["bearer_format"],
                data.get("bearerFormat")
            ),
            flows=forge(
                type_.__annotations__["flows"],
                data.get("flows")
            ),
            open_id_connect_url=forge(
                type_.__annotations__["open_id_connect_url"],
                data.get("openIdConnectUrl")
            ),
            x_basic_info_func=forge(
                type_.__annotations__["x_basic_info_func"],
                data.get("x-basicInfoFunc")
            ),
            x_token_info_func=forge(
                type_.__annotations__["x_token_info_func"],
                data.get("x-tokenInfoFunc")
            ),
            x_api_key_info_func=forge(
                type_.__annotations__["x_api_key_info_func"],
                data.get("x-apiKeyInfoFunc")
            )
        )


register_forge(SecurityScheme, SecurityScheme.forge)


@dataclass
class SecurityRequirement:
    # https://www.asyncapi.com/docs/specifications/v2.2.0#securityRequirementObject
    name: str
    scopes: Sequence[str]
    scheme: SecurityScheme

    @staticmethod
    def forge(
        type_: Type["SecurityRequirement"],
        data: JSONMapping,
        forge: Forge
    ) -> "SecurityRequirement":
        return type_(
            name=forge(type_.__annotations__["name"], data.get("name")),
            scopes=forge(type_.__annotations__["scopes"], data.get("scopes")),
            scheme=forge(type_.__annotations__["scheme"], data.get("scheme"))
        )


register_forge(SecurityRequirement, SecurityRequirement.forge)
