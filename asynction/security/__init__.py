from typing import Sequence

from asynction.common_types import JSONMapping

from .exceptions import UnregisteredSecurityScheme
from .exceptions import UnsupportedSecurityScheme
from .types import SecurityRequirement
from .types import SecurityScheme
from .types import SecuritySchemesType
from .validation import security_handler_factory


def _resolve_security_scheme(
    security: Sequence[JSONMapping], schemes: JSONMapping
) -> Sequence[JSONMapping]:
    new_security = []
    for item in security:
        for scheme_name, scopes in item.items():
            if scheme_name not in schemes:
                raise UnregisteredSecurityScheme
            scheme = schemes[scheme_name]
            new_security.append(dict(name=scheme_name, scopes=scopes, scheme=scheme))

    return new_security


def _resolve_server_security_schemes(
    raw_spec: JSONMapping, schemes: JSONMapping
) -> JSONMapping:
    for name, server in raw_spec.get("servers", {}).items():
        if "security" in server:
            server["security"] = (
                _resolve_security_scheme(server["security"], schemes) or None
            )

    return raw_spec


def resolve_security_schemes(raw_spec: JSONMapping) -> JSONMapping:
    schemes = raw_spec.get("components", {}).get("securitySchemes", {})
    if not schemes:
        return raw_spec
    raw_spec = _resolve_server_security_schemes(raw_spec, schemes)

    return raw_spec


__all__ = [
    "SecurityRequirement",
    "SecurityScheme",
    "SecuritySchemesType",
    "security_handler_factory",
    "resolve_security_schemes",
    "UnregisteredSecurityScheme",
    "UnsupportedSecurityScheme",
]
