from pathlib import Path
from typing import NamedTuple


class FixturePaths(NamedTuple):
    simple: Path


paths = FixturePaths(simple=Path(__file__).parent.joinpath("simple.yml"))
