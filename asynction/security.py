import base64
from functools import partial
from functools import wraps
from typing import Any
from typing import Callable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TypeVar

from flask import Request
from flask import request as current_flask_request
from typing_extensions import TypedDict

from asynction.exceptions import SecurityException
from asynction.types import ApiKeyLocation
from asynction.types import HTTPAuthenticationScheme
from asynction.types import SecurityRequirement
from asynction.types import SecurityScheme
from asynction.types import SecuritySchemesType
from asynction.utils import Decorator
from asynction.utils import Func
from asynction.utils import load_handler


class SecurityInfo(TypedDict, total=False):
    """Security handler function response type.

    One of scopes, scope and one of sub, uid must be present

    Subclass this type to add extra fields to a security handler response
    """

    scopes: Sequence[str]
    scope: str
    sub: Any
    uid: Any


TokenInfoFunc = Callable[[str], SecurityInfo]
BasicInfoFunc = Callable[[str, str, Optional[Sequence[str]]], SecurityInfo]
BearerInfoFunc = Callable[[str, Optional[Sequence[str]], Optional[str]], SecurityInfo]
APIKeyInfoFunc = Callable[[str, Optional[Sequence[str]]], SecurityInfo]
ScopeValidateFunc = Callable[[Sequence[str], Sequence[str]], bool]
InternalSecurityCheckResponse = Optional[SecurityInfo]
InternalSecurityCheck = Callable[[Request], InternalSecurityCheckResponse]
SecurityCheck = Callable[[Request], SecurityInfo]

InternalSecurityRequirement = Tuple[str, Sequence[str]]
SecurityCheckFactory = Callable[
    [InternalSecurityRequirement, SecurityScheme], Optional[InternalSecurityCheck]
]


def unpack_security_requirement(
    requirement: SecurityRequirement,
) -> InternalSecurityRequirement:
    return next(iter(requirement.items()))


def unpack_security_requirements(
    requirements: Sequence[SecurityRequirement],
) -> Sequence[InternalSecurityRequirement]:
    return list(map(unpack_security_requirement, requirements))


def extract_auth_header(request: Request) -> Optional[Tuple[str, str]]:
    authorization = request.headers.get("Authorization")

    if not authorization:
        return None
    try:
        lhs, rhs = authorization.split(None, 1)
        if not lhs or not rhs:
            raise SecurityException(
                "invalid Authorization header"
                " expected: <format> <value>"
                f" found {authorization}"
            )
        return lhs, rhs
    except ValueError as err:
        raise SecurityException from err


def validate_basic(
    request: Request, basic_info_func: BasicInfoFunc, required_scopes: Sequence[str]
) -> Optional[SecurityInfo]:
    auth = extract_auth_header(request)
    if not auth:
        return None

    auth_type, user_pass = auth

    if HTTPAuthenticationScheme(auth_type.lower()) != HTTPAuthenticationScheme.BASIC:
        return None

    try:
        username, password = base64.b64decode(user_pass).decode("latin1").split(":", 1)
    except Exception as err:
        raise SecurityException from err

    if not username or not password:
        raise SecurityException

    token_info = basic_info_func(username, password, required_scopes)
    if token_info is None:
        raise SecurityException

    return token_info


def validate_oauth2_authorization_header(
    request: Request, token_info_func: TokenInfoFunc
) -> Optional[SecurityInfo]:
    """Check that the provided request contains a properly formatted Authorization
    header and invokes the token_info_func on the token inside of the header.
    """
    auth = extract_auth_header(request)
    if not auth:
        return None

    auth_type, token = auth

    if auth_type.lower() != "bearer":
        return None

    token_info = token_info_func(token)
    if token_info is None:
        raise SecurityException

    return token_info


def validate_bearer(
    request: Request,
    bearer_info_func: BearerInfoFunc,
    required_scopes: Sequence[str],
    bearer_format: Optional[str] = None,
) -> Optional[SecurityInfo]:
    """
    Adapted from: https://github.com/zalando/connexion/blob/main/connexion/security/security_handler_factory.py#L221  # noqa: 501
    """
    auth = extract_auth_header(request)
    if not auth:
        return None

    auth_type, token = auth

    if HTTPAuthenticationScheme(auth_type.lower()) != HTTPAuthenticationScheme.BEARER:
        return None

    token_info = bearer_info_func(token, required_scopes, bearer_format)
    if token_info is None:
        raise SecurityException

    return token_info


def validate_scopes(
    required_scopes: Sequence[str], token_scopes: Sequence[str]
) -> bool:
    """Validates that all require scopes are present in the token scopes"""
    missing_scopes = set(required_scopes) - set(token_scopes)
    if missing_scopes:
        raise SecurityException(f"Missing required scopes: {missing_scopes}")

    return not missing_scopes


def load_scope_validate_func(scheme: SecurityScheme) -> ScopeValidateFunc:
    scope_validate_func = None
    if scheme.x_scope_validate_func:
        try:
            scope_validate_func = load_handler(scheme.x_scope_validate_func)
        except (AttributeError, ValueError) as err:
            raise SecurityException from err

    if not scope_validate_func:
        scope_validate_func = validate_scopes

    return scope_validate_func


def load_basic_info_func(scheme: SecurityScheme) -> BasicInfoFunc:
    if not scheme.x_basic_info_func:
        raise SecurityException("Missing basic info func")
    try:
        return load_handler(scheme.x_basic_info_func)
    except (AttributeError, ValueError) as err:
        raise SecurityException from err


def load_token_info_func(scheme: SecurityScheme) -> TokenInfoFunc:
    if not scheme.x_token_info_func:
        raise SecurityException("Missing token info function")
    try:
        return load_handler(scheme.x_token_info_func)
    except (AttributeError, ValueError) as err:
        raise SecurityException from err


def load_api_key_info_func(scheme: SecurityScheme) -> APIKeyInfoFunc:
    if not scheme.x_api_key_info_func:
        raise SecurityException("Missing API Key info function")
    try:
        return load_handler(scheme.x_api_key_info_func)
    except (AttributeError, ValueError) as err:
        raise SecurityException from err


def load_bearer_info_func(scheme: SecurityScheme) -> BearerInfoFunc:
    if not scheme.x_bearer_info_func:
        raise SecurityException("Missing Bearer info function")
    try:
        return load_handler(scheme.x_bearer_info_func)
    except (AttributeError, ValueError) as err:
        raise SecurityException from err


def validate_token_info(
    token_info: InternalSecurityCheckResponse,
    scope_validate_func: ScopeValidateFunc,
    required_scopes: Sequence[str],
) -> InternalSecurityCheckResponse:
    scopes: Optional[Sequence[str]] = None
    if not token_info:
        return None

    if "scopes" in token_info:
        scopes = token_info.get("scopes")
    elif "scope" in token_info:
        scope = token_info.get("scope")
        if isinstance(scope, str):
            scopes = scope.split()
        else:
            raise ValueError("'scope' should be a string")

    if not scopes:
        raise ValueError("missing scopes in token info")

    if not scope_validate_func(required_scopes, scopes):
        raise SecurityException(
            f"Invalid scopes: required: {required_scopes}, provided: {scopes}"
        )

    return token_info


def build_http_security_check(
    requirement: InternalSecurityRequirement, scheme: SecurityScheme
) -> Optional[InternalSecurityCheck]:
    _, required_scopes = requirement

    if scheme.scheme == HTTPAuthenticationScheme.BASIC:
        basic_info_func = load_basic_info_func(scheme)

        return partial(
            validate_basic,
            basic_info_func=basic_info_func,
            required_scopes=required_scopes,
        )
    elif scheme.scheme == HTTPAuthenticationScheme.BEARER:
        bearer_info_func = load_bearer_info_func(scheme)
        bearer_format = scheme.bearer_format

        return partial(
            validate_bearer,
            bearer_info_func=bearer_info_func,
            required_scopes=required_scopes,
            bearer_format=bearer_format,
        )
    else:
        return None


def build_http_api_key_security_check(
    requirement: InternalSecurityRequirement, scheme: SecurityScheme
) -> Optional[InternalSecurityCheck]:
    api_key_info_func = load_api_key_info_func(scheme)
    _, required_scopes = requirement

    def http_api_key_security_check(request: Request) -> InternalSecurityCheckResponse:
        api_key = None
        requests_dict = {
            ApiKeyLocation.QUERY: request.args,
            ApiKeyLocation.HEADER: request.headers,
            ApiKeyLocation.COOKIE: request.cookies,
        }
        try:
            # mypy insists this is checked
            if scheme.in_ is not None and scheme.name is not None:
                api_key = requests_dict[scheme.in_][scheme.name]
        except KeyError:
            return None

        if api_key is None:
            return None

        return api_key_info_func(api_key, required_scopes)

    return http_api_key_security_check


def build_oauth2_security_check(
    requirement: InternalSecurityRequirement, scheme: SecurityScheme
) -> Optional[InternalSecurityCheck]:
    token_info_func = load_token_info_func(scheme)
    scope_validate_func = load_scope_validate_func(scheme)

    _, required_scopes = requirement

    def oauth2_security_check(request: Request) -> InternalSecurityCheckResponse:
        token_info = validate_oauth2_authorization_header(request, token_info_func)

        return validate_token_info(token_info, scope_validate_func, required_scopes)

    return oauth2_security_check


# Dispatch table mapping SecuritySchemesType to security check builder
_BUILDER_DISPATCH: Mapping[SecuritySchemesType, SecurityCheckFactory] = {
    SecuritySchemesType.HTTP: build_http_security_check,
    SecuritySchemesType.OAUTH2: build_oauth2_security_check,
    SecuritySchemesType.HTTP_API_KEY: build_http_api_key_security_check,
}


def build_security_handler(
    security: Sequence[InternalSecurityRequirement],
    security_schemes: Mapping[str, SecurityScheme],
) -> SecurityCheck:
    # build a list of security validators based on the provided security schemes
    security_checks: List[InternalSecurityCheck] = []

    for requirement in security:
        requirement_name, _ = requirement
        scheme = security_schemes[requirement_name]
        builder = _BUILDER_DISPATCH.get(scheme.type)
        if not builder:
            continue
        check = builder(requirement, scheme)
        if not check:
            continue
        security_checks.append(check)

    def security_handler(request: Request) -> SecurityInfo:

        # apply the security schemes in the order listed in the API file
        for check in security_checks:

            # if a security check fails if will raise the appropriate exception
            # if the security check passes it will return a dict of kwargs to pass to the handler   # noqa: 501
            # if the check is not applicable based on lack provided argument the check will return None indicating   # noqa: 501
            # that the next (if any) check should be run.
            security_args = check(request)
            if security_args:
                return security_args

        raise SecurityException("No checks passed")

    return security_handler


T = TypeVar("T")


def security_handler_factory(
    security_requirements: Sequence[SecurityRequirement],
    security_schemes: Mapping[str, SecurityScheme],
) -> Decorator[T]:
    """
    Build a security handler decorator based on security object and securitySchemes provided in the API file.  # noqa: 501
    """
    unpacked_security = unpack_security_requirements(security_requirements)
    security_handler = build_security_handler(unpacked_security, security_schemes)

    def decorator(handler: Func[T]) -> Func[T]:
        if handler is None:
            raise SecurityException("invalid or missing handler")

        @wraps(handler)
        def handler_with_security(*args: Any, **kwargs: Any) -> T:
            # match the args that connexion passes to handlers after a security check
            token_info = security_handler(current_flask_request)
            user = token_info.get("sub", token_info.get("uid"))
            return handler(*args, user=user, token_info=token_info, **kwargs)

        return handler_with_security

    return decorator
