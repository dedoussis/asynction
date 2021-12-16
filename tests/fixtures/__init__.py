from pathlib import Path
from typing import NamedTuple


class FixturePaths(NamedTuple):
    simple: Path
    echo: Path
    simple_with_servers: Path
    security: Path
    security_oauth2: Path
    namespace_security: Path
    array_vs_tuple: Path


paths = FixturePaths(
    simple=Path(__file__).parent / "simple.yml",
    echo=Path(__file__).parent / "echo.yml",
    simple_with_servers=Path(__file__).parent / "simple_with_servers.yml",
    security=Path(__file__).parent / "security.yaml",
    security_oauth2=Path(__file__).parent / "security_oauth2.yaml",
    namespace_security=Path(__file__).parent / "namespace_security.yaml",
    array_vs_tuple=Path(__file__).parent / "array_vs_tuple.yaml",
)
