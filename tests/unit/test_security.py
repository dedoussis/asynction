import base64

import pytest
from flask import Flask
from flask import request as current_flask_request

from asynction.exceptions import SecurityException
from asynction.security import build_http_api_key_security_check
from asynction.security import build_http_security_check
from asynction.security import build_oauth2_security_check
from asynction.security import build_security_handler
from asynction.security import extract_auth_header
from asynction.security import load_api_key_info_func
from asynction.security import load_basic_info_func
from asynction.security import load_token_info_func
from asynction.security import security_handler_factory
from asynction.types import ApiKeyLocation
from asynction.types import HTTPAuthenticationScheme
from asynction.types import OAuth2Flow
from asynction.types import OAuth2Flows
from asynction.types import SecurityScheme
from asynction.types import SecuritySchemesType
from tests.fixtures import FixturePaths
from tests.fixtures import handlers


def test_extract_auth_header():
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"basic {basic_auth}"}
        c.post(headers=headers)
        extract_auth_header(current_flask_request)


def test_extract_auth_header_fails_missing_header():
    with Flask(__name__).test_client() as c:
        c.post()
        assert extract_auth_header(current_flask_request) is None


def test_extract_auth_header_fails_invalid_header():
    with Flask(__name__).test_client() as c:
        headers = {"Authorization": "invalid"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            extract_auth_header(current_flask_request)


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
        in_=ApiKeyLocation.QUERY,
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
        x_bearer_info_func="tests.fixtures.handlers.bearer_info",
    )
    check = build_http_security_check(requirement, scheme)
    assert callable(check)


def test_build_http_api_key_security_check():
    requirement = ("test", [])
    scheme = SecurityScheme(
        SecuritySchemesType.HTTP_API_KEY,
        name="api_key",
        in_=ApiKeyLocation.QUERY,
        x_api_key_info_func="tests.fixtures.handlers.api_key_info",
    )
    check = build_http_api_key_security_check(requirement, scheme)
    assert callable(check)


def test_build_http_api_key_security_scheme_fails_without_name():
    with pytest.raises(ValueError):
        SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            in_=ApiKeyLocation.QUERY,
            x_api_key_info_func="tests.fixtures.handlers.api_key_info",
        )


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
            x_bearer_info_func="tests.fixtures.handlers.bearer_info",
        ),
        api_key=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_=ApiKeyLocation.QUERY,
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


def test_build_security_handler_with_invalid_handler():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        )
    )
    factory = security_handler_factory(requirements, schemes)
    with pytest.raises(SecurityException):
        factory(None)


def test_http_basic_works():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"basic {basic_auth}"}
        c.post(headers=headers)
        handler_with_security()


def test_http_basic_fails():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:wrong".encode()).decode()
        headers = {"Authorization": f"basic {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(ConnectionRefusedError):
            handler_with_security()


def test_http_basic_fails_missing_basic_info():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info_fake",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    with pytest.raises(AttributeError):
        factory = security_handler_factory(requirements, schemes)
        factory(on_connect)


def test_http_basic_fails_because_basic_info_returns_none():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info_bad",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"basic {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(ConnectionRefusedError):
            handler_with_security()


def test_http_bearer_works():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BEARER,
            bearer_format="test",
            x_bearer_info_func="tests.fixtures.handlers.bearer_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"bearer {basic_auth}"}
        c.post(headers=headers)
        handler_with_security()


def test_http_bearer_fails_with_no_auth_header():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BEARER,
            bearer_format="test",
            x_bearer_info_func="tests.fixtures.handlers.bearer_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        c.post()
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_bearer_fails_with_not_bearer():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BEARER,
            bearer_format="test",
            x_bearer_info_func="tests.fixtures.handlers.bearer_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"not_bearer {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_bearer_fails_with_invalid_header_format():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BEARER,
            bearer_format="test",
            x_bearer_info_func="tests.fixtures.handlers.bearer_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"{basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_bearer_fails_bad_bearer_info_func():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BEARER,
            bearer_format="test",
            x_bearer_info_func="tests.fixtures.handlers.bearer_info_bad",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"bearer {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_api_key_works_header():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_=ApiKeyLocation.HEADER,
            x_api_key_info_func="tests.fixtures.handlers.api_key_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"api_key": f"{basic_auth}"}
        c.post(headers=headers)
        handler_with_security()


def test_http_api_key_works_query():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_=ApiKeyLocation.QUERY,
            x_api_key_info_func="tests.fixtures.handlers.api_key_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        c.post(f"/?api_key={basic_auth}")
        handler_with_security()


def test_http_api_key_works_cookie():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_=ApiKeyLocation.COOKIE,
            x_api_key_info_func="tests.fixtures.handlers.api_key_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        c.set_cookie("test", "api_key", basic_auth)
        c.post()
        handler_with_security()


def test_http_api_key_fails_missing_api_key_info_func():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_=ApiKeyLocation.COOKIE,
            x_api_key_info_func="tests.fixtures.handlers.api_key_info_fake",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    with pytest.raises(AttributeError):
        factory = security_handler_factory(requirements, schemes)
        factory(on_connect)


def test_http_api_key_fails_missing_cookie():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_=ApiKeyLocation.COOKIE,
            x_api_key_info_func="tests.fixtures.handlers.api_key_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        c.set_cookie("test", "wrong", "value")

        c.post()
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_api_fails_bad_api_key_info_func():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP_API_KEY,
            name="api_key",
            in_=ApiKeyLocation.HEADER,
            x_api_key_info_func="tests.fixtures.handlers.api_key_info_bad",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"api_key": f"{basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_oauth2_works():
    requirements = [{"basic": ["a"]}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.OAUTH2,
            flows=OAuth2Flows(
                implicit=OAuth2Flow(authorization_url="https://test", scopes={"a": "A"})
            ),
            x_token_info_func="tests.fixtures.handlers.token_info",
            x_scope_validate_func="asynction.security.validate_scopes",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"bearer {basic_auth}"}
        c.post(headers=headers)
        handler_with_security()


def test_oauth2_fails_missing_token_info_func():
    requirements = [{"basic": ["a"]}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.OAUTH2,
            flows=OAuth2Flows(
                implicit=OAuth2Flow(authorization_url="https://test", scopes={"a": "A"})
            ),
            x_token_info_func="tests.fixtures.handlers.token_info_fake",
            x_scope_validate_func="asynction.security.validate_scopes",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    with pytest.raises(AttributeError):
        factory = security_handler_factory(requirements, schemes)
        factory(on_connect)


def test_oauth2_fails_missing_scopes():
    requirements = [{"basic": ["z"]}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.OAUTH2,
            flows=OAuth2Flows(
                implicit=OAuth2Flow(authorization_url="https://test", scopes={"z": "Z"})
            ),
            x_token_info_func="tests.fixtures.handlers.token_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"bearer {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_oauth2_fails_bad_token_info_func():
    requirements = [{"basic": ["a"]}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.OAUTH2,
            flows=OAuth2Flows(
                implicit=OAuth2Flow(authorization_url="https://test", scopes={"a": "A"})
            ),
            x_token_info_func="tests.fixtures.handlers.token_info_bad",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"bearer {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_oauth2_fails_missing_auth_header():
    requirements = [{"basic": ["a"]}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.OAUTH2,
            flows=OAuth2Flows(
                implicit=OAuth2Flow(authorization_url="https://test", scopes={"a": "A"})
            ),
            x_token_info_func="tests.fixtures.handlers.token_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        c.post()
        with pytest.raises(SecurityException):
            handler_with_security()


def test_oauth2_fails_invalid_header_format():
    requirements = [{"basic": ["a"]}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.OAUTH2,
            flows=OAuth2Flows(
                implicit=OAuth2Flow(authorization_url="https://test", scopes={"a": "A"})
            ),
            x_token_info_func="tests.fixtures.handlers.token_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"not_bearer {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_basic_missing_auth_header():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        c.post()
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_basic_invalid_auth_header():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"basic{basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_basic_invalid_basic_auth_format():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:".encode()).decode()
        headers = {"Authorization": f"basic {basic_auth}"}
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()


def test_http_basic_invalid_basic_auth_scheme():
    requirements = [{"basic": []}]
    schemes = dict(
        basic=SecurityScheme(
            SecuritySchemesType.HTTP,
            scheme=HTTPAuthenticationScheme.BASIC,
            x_basic_info_func="tests.fixtures.handlers.basic_info",
        )
    )

    def on_connect(*args, **kwargs):
        print(args, kwargs)

    factory = security_handler_factory(requirements, schemes)
    handler_with_security = factory(on_connect)
    with Flask(__name__).test_client() as c:
        basic_auth = base64.b64encode("username:password".encode()).decode()
        headers = {"Authorization": f"bearer {basic_auth}"}  # expects basic
        c.post(headers=headers)
        with pytest.raises(SecurityException):
            handler_with_security()
