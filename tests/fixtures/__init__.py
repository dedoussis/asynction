from pathlib import Path
from typing import NamedTuple


class FixturePaths(NamedTuple):
    simple: Path
    namespaces: Path
    echo: Path
    echo_with_bindings: Path


paths = FixturePaths(
    simple=Path(__file__).parent.joinpath("simple.yml"),
    namespaces=Path(__file__).parent.joinpath("namespaces.yml"),
    echo=Path(__file__).parent.joinpath("echo.yml"),
    echo_with_bindings=Path(__file__).parent.joinpath("echo_with_bindings.yml"),
)
