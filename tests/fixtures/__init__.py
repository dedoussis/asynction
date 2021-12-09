from pathlib import Path
from typing import NamedTuple


class FixturePaths(NamedTuple):
    simple: Path
    echo: Path
    simple_with_servers: Path
    security: Path
    security_oauth2: Path
    namespace_security: Path
    multi1: Path
    multi2: Path


paths = FixturePaths(
    simple=Path(__file__).parent.joinpath("simple.yml"),
    echo=Path(__file__).parent.joinpath("echo.yml"),
    simple_with_servers=Path(__file__).parent.joinpath("simple_with_servers.yml"),
    security=Path(__file__).parent.joinpath("security.yaml"),
    security_oauth2=Path(__file__).parent.joinpath("security_oauth2.yaml"),
    namespace_security=Path(__file__).parent.joinpath("namespace_security.yaml"),
    multi1=Path(__file__).parent.joinpath("multi1.yaml"),
    multi2=Path(__file__).parent.joinpath("multi2.yaml"),
)
