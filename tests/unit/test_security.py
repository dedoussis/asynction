from asynction.security import build_http_api_key_security_check
from asynction.security import build_http_security_check
from asynction.security import build_oauth2_security_check
from asynction.security import build_security_handler
from asynction.security import load_api_key_info_func
from asynction.security import load_basic_info_func
from asynction.security import load_token_info_func
from asynction.types import HTTPAuthenticationScheme
from asynction.types import OAuth2Flow
from asynction.types import OAuth2Flows
from asynction.types import SecurityScheme
from asynction.types import SecuritySchemesType
from tests.fixtures import FixturePaths
from tests.fixtures import handlers


def test_load_basic_info_func():
    scheme = SecurityScheme(
        SecuritySchemesType.HTTP,
        scheme=HTTPAuthenticationScheme.BASIC,
        x_basic_info_func="tests.fixtures.handlers.basic_info",
    )
    assert load_basic_info_func(scheme) == handlers.basic_info


def test_load_api_key_info_func(fixture_paths: FixturePaths):
    scheme = SecurityScheme(
        SecuritySchemesType.HTTP_API_KEY,
        name="api_key",
        in_="query",
        x_api_key_info_func="tests.fixtures.handlers.api_key_info",
    )
    assert load_api_key_info_func(scheme) == handlers.api_key_info


def test_load_token_info_func(fixture_paths: FixturePaths):
    scheme = SecurityScheme(
        SecuritySchemesType.OAUTH2,
        flows=OAuth2Flows(implicit=OAuth2Flow(authorization_url="", scopes={"a": "a"})),
        x_token_info_func="tests.fixtures.handlers.token_info",
    )
    assert load_token_info_func(scheme) == handlers.token_info


def test_build_basic_http_security_check():
    requirement = ("test", [])
    scheme = SecurityScheme(
        SecuritySchemesType.HTTP,
        scheme=HTTPAuthenticationScheme.BASIC,
        x_basic_info_func="tests.fixtures.handlers.basic_info",
    )
    check = build_http_security_check(requirement, scheme)
    assert callable(check)


def test_build_bearer_http_security_check():
    requirement = ("test", [])
    scheme = SecurityScheme(
        SecuritySchemesType.HTTP,
        scheme=HTTPAuthenticationScheme.BEARER,
        x_api_key_info_func="tests.fixtures.handlers.bearer_info",
    )
    check = build_http_security_check(requirement, scheme)
    assert callable(check)


def test_build_http_api_key_security_check():
    requirement = ("test", [])
    scheme = SecurityScheme(
        SecuritySchemesType.HTTP_API_KEY,
        name="api_key",
        in_="query",
        x_api_key_info_func="tests.fixtures.handlers.api_key_info",
    )
    check = build_http_api_key_security_check(requirement, scheme)
    assert callable(check)


def test_build_oauth2_security_check():
    requirement = ("test", [])
    scheme = SecurityScheme(
        SecuritySchemesType.OAUTH2,
        flows=OAuth2Flows(implicit=OAuth2Flow(authorization_url="", scopes={"a": "a"})),
        x_token_info_func="tests.fixtures.handlers.token_info",
    )
    check = build_oauth2_security_check(requirement, scheme)
    assert callable(check)


def test_build_security_check_list():
    requirements = [
        ("basic", []),
        ("bearer", []),
        ("api_key", []),
        ("oauth2", ["a"]),
    ]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        ),
        bearer=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BEARER,
            x_api_key_info_func="tests.fixtures.handlers.bearer_info",
        ),
        api_key=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_="query",
            x_api_key_info_func="tests.fixtures.handlers.api_key_info",
        ),
        oauth2=SecurityScheme(
            SecuritySchemesType.OAUTH2,
            flows=OAuth2Flows(
                implicit=OAuth2Flow(authorization_url="", scopes={"a": "a"})
            ),
            x_token_info_func="tests.fixtures.handlers.token_info",
        ),
    )

    check = build_security_handler(requirements, schemes)
    assert check
    assert callable(check)
