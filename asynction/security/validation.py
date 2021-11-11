import base64
import http.cookies
from functools import wraps
from typing import Callable
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Union

from flask import Request
from flask import request as current_flask_request

from asynction.loader import load_handler
from asynction.security import SecurityRequirement
from asynction.security import SecuritySchemesType

from .exceptions import SecurityException
from .exceptions import UnsupportedSecurityScheme
from .types import HTTPSecuritySchemeType
from .types import SecurityScheme

TokenInfoFunc = Callable[[str], Mapping]
BasicInfoFunc = Callable[[str, str, Optional[Sequence[str]]], Mapping]
APIKeyInfoFunc = Callable[[str, Optional[Sequence[str]], Optional[str]], Mapping]


def validate_basic(
    request: Request, basic_info_func: BasicInfoFunc, required_scopes: Sequence[str]
) -> Union[Mapping, None]:
    authorization = request.headers.get("Authorization")

    if not authorization:
        return None
    try:
        auth_type, user_pass = authorization.split(None, 1)
    except ValueError as err:
        raise SecurityException from err

    if HTTPSecuritySchemeType(auth_type.lower()) != HTTPSecuritySchemeType.BASIC:
        return None
    try:
        username, password = base64.b64decode(user_pass).decode("latin1").split(":", 1)
    except Exception as err:
        raise SecurityException from err

    token_info = basic_info_func(username, password, required_scopes)
    if token_info is None:
        raise SecurityException

    return token_info


def validate_authorization_header(
    request: Request, token_info_func: TokenInfoFunc
) -> Union[Mapping, None]:
    """Check that the provided request contains a properly formatted Authorization
    header and invokes the token_info_func on the token inside of the header.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None

    try:
        auth_type, token = authorization.split(None, 1)
    except ValueError as err:
        raise SecurityException from err

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
) -> Union[Mapping, None]:
    """
    Adapted from: https://github.com/zalando/connexion/blob/main/connexion/security/security_handler_factory.py#L221  # noqa: 501
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None

    try:
        auth_type, token = authorization.split(None, 1)
    except ValueError as err:
        raise SecurityException from err

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
    requirement: SecurityRequirement,
) -> Callable[[Request], Mapping]:
    required_scopes = requirement.scopes
    if requirement.scheme.scheme == HTTPSecuritySchemeType.BASIC:
        basic_info_func = load_basic_info_func(requirement.scheme)

        def http_security_check(request: Request):
            token_info = validate_basic(request, basic_info_func, required_scopes)
            if token_info is None:
                return None

            token_scopes = token_info.get("scope", token_info.get("scopes", ""))

            validate_scopes(required_scopes, token_scopes)

            return token_info

        return http_security_check
    elif requirement.scheme.scheme == HTTPSecuritySchemeType.BEARER:
        api_key_info_func = load_api_key_info_func(requirement.scheme)
        bearer_format = requirement.scheme.bearer_format

        def http_bearer_security_check(request: Request):
            token_info = validate_api_key(
                request, api_key_info_func, required_scopes, bearer_format
            )
            if token_info is None:
                return None

            token_scopes = token_info.get("scope", token_info.get("scopes", ""))

            validate_scopes(required_scopes, token_scopes)

            return token_info

        return http_bearer_security_check
    else:
        raise UnsupportedSecurityScheme


def get_cookie_value(cookies, name):
    """
    Returns cookie value by its name. None if no such value.
    :param cookies: str: cookies raw data
    :param name: str: cookies key

    Borrowed from https://github.com/zalando/connexion/blob/main/connexion/security/security_handler_factory.py#L206  # noqa: 501
    """
    cookie_parser = http.cookies.SimpleCookie()
    cookie_parser.load(str(cookies))
    try:
        return cookie_parser[name].value
    except KeyError:
        return None


def build_http_api_key_security_check(
    requirement: SecurityRequirement,
) -> Callable[[Request], Mapping]:
    api_key_info_func = load_api_key_info_func(requirement.scheme)
    required_scopes = requirement.scopes
    api_key_in = requirement.scheme.in_
    api_key_name = requirement.scheme.name
    if api_key_name is None:
        raise SecurityException("invalid api key name specified")
    if api_key_in not in ["query", "header", "cookie"]:
        raise SecurityException("invalid api key location specified")

    def http_api_key_security_check(request: Request):
        def _immutable_pop(_dict, key):
            """
            Pops the key from an immutable dict and returns the value that was popped,
            and a new immutable dict without the popped key.
            """
            cls = type(_dict)
            try:
                _dict = _dict.to_dict(flat=False)
                return _dict.pop(key)[0], cls(_dict)
            except AttributeError:
                _dict = dict(_dict.items())
                return _dict.pop(key), cls(_dict)

        if api_key_in == "query":
            if api_key_name is not None:
                apikey = request.args.get(api_key_name)
        elif api_key_in == "header":
            if api_key_name is not None:
                apikey = request.headers.get(api_key_name)
        elif api_key_in == "cookie":
            cookieslist = request.headers.get("Cookie")
            apikey = get_cookie_value(cookieslist, api_key_name)
        else:
            return None
        if apikey is None:
            return None

        token_info = api_key_info_func(apikey, required_scopes, None)
        if token_info is None:
            return None

        token_scopes = token_info.get("scope", token_info.get("scopes", ""))

        validate_scopes(required_scopes, token_scopes)

        return token_info

    return http_api_key_security_check


def build_oauth2_security_check(
    requirement: SecurityRequirement,
) -> Callable[[Request], Mapping]:
    token_info_func = load_token_info_func(requirement.scheme)
    required_scopes = requirement.scopes

    def oauth2_security_check(request: Request):
        token_info = validate_authorization_header(request, token_info_func)
        if token_info is None:
            return None

        token_scopes = token_info.get("scope", token_info.get("scopes", ""))

        validate_scopes(required_scopes, token_scopes)

        return token_info

    return oauth2_security_check


# Dispatch table mapping SecuritySchemesType to security check builder
_BUILDER_DISPATCH = {
    SecuritySchemesType.HTTP: build_http_security_check,
    SecuritySchemesType.OAUTH2: build_oauth2_security_check,
    SecuritySchemesType.HTTP_API_KEY: build_http_api_key_security_check,
}


def build_security_handler(
    security: Sequence[SecurityRequirement],
) -> Callable[[Request], Mapping]:
    # build a list of security validators based on the provided security schemes
    security_checks = []

    for requirement in security:
        scheme = SecuritySchemesType(requirement.scheme.type)
        builder = _BUILDER_DISPATCH.get(scheme)
        if not builder:
            raise UnsupportedSecurityScheme
        security_checks.append(builder(requirement))

    def security_handler(request: Request) -> Mapping:

        try:
            # apply the security schemes in the order listed in the API file
            for check in security_checks:

                # if a security check fails if will raise the appropriate exception
                # if the security check passes it will return a dict of kwargs to pass to the handler   # noqa: 501
                # if the check is not applicable based on lack provided argument the check will return None indicating   # noqa: 501
                # that the next (if any) check should be run.
                security_args = check(request)
                if security_args:
                    return security_args
            else:
                raise SecurityException("No checks passed")
        except SecurityException as err:
            raise ConnectionRefusedError(str(err)) from err

    return security_handler


def security_handler_factory(security: Sequence[SecurityRequirement]) -> Callable:
    """
    Build a security handler decorator based on security object and securitySchemes provided in the API file.  # noqa: 501
    """
    security_handler = build_security_handler(security)

    def decorator(handler: Callable):
        if handler is None:
            raise SecurityException("invalid or missing handler")

        @wraps(handler)
        def handler_with_security(*args, **kwargs):
            security_args = security_handler(current_flask_request)
            return handler(*args, **security_args, **kwargs)

        return handler_with_security

    return decorator
