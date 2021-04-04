from pathlib import Path
from typing import NamedTuple


class FixturePaths(NamedTuple):
    simple: Path
    namespaces: Path
    echo: Path


paths = FixturePaths(
    simple=Path(__file__).parent.joinpath("simple.yml"),
    namespaces=Path(__file__).parent.joinpath("namespaces.yml"),
    echo=Path(__file__).parent.joinpath("echo.yml"),
)
