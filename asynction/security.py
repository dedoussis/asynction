import base64
from functools import wraps
from http.cookies import SimpleCookie
from typing import Callable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

from flask import Request
from flask import request as current_flask_request

from asynction.exceptions import SecurityException
from asynction.types import HTTPAuthenticationScheme
from asynction.types import SecurityRequirement
from asynction.types import SecurityScheme
from asynction.types import SecuritySchemesType
from asynction.utils import load_handler

TokenInfoFunc = Callable[[str], Mapping]
BasicInfoFunc = Callable[[str, str, Optional[Sequence[str]]], Mapping]
APIKeyInfoFunc = Callable[[str, Optional[Sequence[str]], Optional[str]], Mapping]
ScopeValidateFunc = Callable[[Sequence[str], Sequence[str]], bool]
InternalSecurityCheckResponse = Tuple[Optional[Mapping], Optional[str]]
InternalSecurityCheck = Callable[[Request], InternalSecurityCheckResponse]
SecurityCheck = Callable[[Request], Mapping]

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
        return lhs, rhs
    except ValueError as err:
        raise SecurityException from err


def validate_basic(
    request: Request, basic_info_func: BasicInfoFunc, required_scopes: Sequence[str]
) -> Optional[Mapping]:
    auth = extract_auth_header(request)
    if not auth:
        return None
    auth_type, user_pass = auth
    if not auth_type or not user_pass:
        raise SecurityException

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


def validate_authorization_header(
    request: Request, token_info_func: TokenInfoFunc
) -> Optional[Mapping]:
    """Check that the provided request contains a properly formatted Authorization
    header and invokes the token_info_func on the token inside of the header.
    """
    auth = extract_auth_header(request)
    if not auth:
        return None
    auth_type, token = auth
    if not auth_type or not token:
        raise SecurityException

    if auth_type.lower() != "bearer":
        return None

    token_info = token_info_func(token)
    if token_info is None:
        raise SecurityException

    return token_info


def validate_api_key(
    request: Request,
    api_key_info_func: APIKeyInfoFunc,
    required_scopes: Sequence[str],
    bearer_format: Optional[str] = None,
) -> Optional[Mapping]:
    """
    Adapted from: https://github.com/zalando/connexion/blob/main/connexion/security/security_handler_factory.py#L221  # noqa: 501
    """
    auth = extract_auth_header(request)
    if not auth:
        return None
    auth_type, token = auth

    if not auth_type or not token:
        raise SecurityException

    if auth_type.lower() != "bearer":
        return None

    token_info = api_key_info_func(token, required_scopes, bearer_format)
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
        scope_validate_func = load_handler(scheme.x_scope_validate_func)

    if not scope_validate_func:
        scope_validate_func = validate_scopes

    return scope_validate_func


def load_basic_info_func(scheme: SecurityScheme) -> BasicInfoFunc:
    if scheme.x_basic_info_func is not None:
        basic_info_func = load_handler(scheme.x_basic_info_func)
        if not basic_info_func:
            raise SecurityException("Missing basic info func")
        return basic_info_func
    else:
        raise SecurityException("Missing basic info func")


def load_token_info_func(scheme: SecurityScheme) -> TokenInfoFunc:
    if scheme.x_token_info_func is not None:
        token_info_func = load_handler(scheme.x_token_info_func)
        if not token_info_func:
            raise SecurityException("Missing token info function")
        return token_info_func
    else:
        raise SecurityException("Missing token info function")


def load_api_key_info_func(scheme: SecurityScheme) -> APIKeyInfoFunc:
    if scheme.x_api_key_info_func is not None:
        token_info_func = load_handler(scheme.x_api_key_info_func)
        if not token_info_func:
            raise SecurityException("Missing API Key info function")
        return token_info_func
    else:
        raise SecurityException("Missing API Key info function")


def build_http_security_check(
    requirement: InternalSecurityRequirement, scheme: SecurityScheme
) -> Optional[InternalSecurityCheck]:
    _, required_scopes = requirement
    if scheme.scheme == HTTPAuthenticationScheme.BASIC:
        basic_info_func = load_basic_info_func(scheme)
        scope_validate_func = load_scope_validate_func(scheme)

        def http_security_check(request: Request) -> InternalSecurityCheckResponse:
            token_info = validate_basic(request, basic_info_func, required_scopes)
            if token_info is None:
                return None, None

            token_scopes = token_info.get("scope", token_info.get("scopes", ""))

            if not scope_validate_func(required_scopes, token_scopes):
                return (
                    None,
                    f"Invalid scopes: required: {required_scopes}, provided: {token_scopes}",  # noqa: 501
                )

            return token_info, None

        return http_security_check
    elif scheme.scheme == HTTPAuthenticationScheme.BEARER:
        api_key_info_func = load_api_key_info_func(scheme)
        scope_validate_func = load_scope_validate_func(scheme)

        bearer_format = scheme.bearer_format

        def http_bearer_security_check(
            request: Request,
        ) -> InternalSecurityCheckResponse:
            token_info = validate_api_key(
                request, api_key_info_func, required_scopes, bearer_format
            )
            if token_info is None:
                return None, None

            token_scopes = token_info.get("scope", token_info.get("scopes", ""))

            if not scope_validate_func(required_scopes, token_scopes):
                return (
                    None,
                    f"Invalid scopes: required: {required_scopes}, provided: {token_scopes}",  # noqa: 501
                )

            return token_info, None

        return http_bearer_security_check
    else:
        return None


def get_cookie_value(cookies: str, name: str) -> Optional[str]:
    """
    Returns cookie value by its name. None if no such value.
    :param cookies: str: cookies raw data
    :param name: str: cookies key

    Borrowed from https://github.com/zalando/connexion/blob/main/connexion/security/security_handler_factory.py#L206  # noqa: 501
    """
    cookie_parser: SimpleCookie = SimpleCookie()
    cookie_parser.load(str(cookies))
    try:
        return cookie_parser[name].value
    except KeyError:
        return None


def build_http_api_key_security_check(
    requirement: InternalSecurityRequirement, scheme: SecurityScheme
) -> Optional[InternalSecurityCheck]:
    api_key_info_func = load_api_key_info_func(scheme)
    scope_validate_func = load_scope_validate_func(scheme)

    _, required_scopes = requirement
    api_key_in = scheme.in_
    api_key_name = scheme.name
    if api_key_name is None:
        raise SecurityException("invalid api key name specified")
    if api_key_in not in ["query", "header", "cookie"]:
        raise SecurityException("invalid api key location specified")

    def http_api_key_security_check(request: Request) -> InternalSecurityCheckResponse:
        api_key = None

        if api_key_in == "query":
            if api_key_name is not None:
                api_key = request.args.get(api_key_name)
        elif api_key_in == "header":
            if api_key_name is not None:
                api_key = request.headers.get(api_key_name)
        elif api_key_in == "cookie":
            cookies_list = request.headers.get("Cookie")
            if cookies_list and api_key_name is not None:
                api_key = get_cookie_value(cookies_list, api_key_name)
        else:
            return None, None

        if api_key is None:
            return None, None

        token_info = api_key_info_func(api_key, required_scopes, None)
        if token_info is None:
            return None, None

        token_scopes = token_info.get("scope", token_info.get("scopes", ""))

        if not scope_validate_func(required_scopes, token_scopes):
            return (
                None,
                f"Invalid scopes: required: {required_scopes}, provided: {token_scopes}",  # noqa: 501
            )

        return token_info, None

    return http_api_key_security_check


def build_oauth2_security_check(
    requirement: InternalSecurityRequirement, scheme: SecurityScheme
) -> Optional[InternalSecurityCheck]:
    token_info_func = load_token_info_func(scheme)
    _, required_scopes = requirement

    def oauth2_security_check(request: Request) -> InternalSecurityCheckResponse:
        token_info = validate_authorization_header(request, token_info_func)
        scope_validate_func = load_scope_validate_func(scheme)

        if token_info is None:
            return None, None

        token_scopes = token_info.get("scope", token_info.get("scopes", ""))

        if not scope_validate_func(required_scopes, token_scopes):
            raise SecurityException(
                f"Invalid scopes: required: {required_scopes}, provided: {token_scopes}"  # noqa: 501
            )

        return token_info, None

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

    def security_handler(request: Request) -> Mapping:

        # apply the security schemes in the order listed in the API file
        for check in security_checks:

            # if a security check fails if will raise the appropriate exception
            # if the security check passes it will return a dict of kwargs to pass to the handler   # noqa: 501
            # if the check is not applicable based on lack provided argument the check will return None indicating   # noqa: 501
            # that the next (if any) check should be run.
            security_args, err = check(request)
            if err:
                raise SecurityException(err)
            if security_args:
                return security_args
        else:
            raise SecurityException("No checks passed")

    return security_handler


def security_handler_factory(
    security: Sequence[SecurityRequirement],
    security_schemes: Mapping[str, SecurityScheme],
) -> Callable:
    """
    Build a security handler decorator based on security object and securitySchemes provided in the API file.  # noqa: 501
    """
    unpacked_security = unpack_security_requirements(security)
    security_handler = build_security_handler(unpacked_security, security_schemes)

    def decorator(handler: Callable):
        if handler is None:
            raise SecurityException("invalid or missing handler")

        @wraps(handler)
        def handler_with_security(*args, **kwargs):
            security_args = security_handler(current_flask_request)
            return handler(*args, **security_args, **kwargs)

        return handler_with_security

    return decorator
