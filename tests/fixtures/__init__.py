from pathlib import Path
from typing import NamedTuple


class FixturePaths(NamedTuple):
    simple: Path
    echo: Path
    simple_with_servers: Path


paths = FixturePaths(
    simple=Path(__file__).parent.joinpath("simple.yml"),
    echo=Path(__file__).parent.joinpath("echo.yml"),
    simple_with_servers=Path(__file__).parent.joinpath("simple_with_servers.yml"),
)
