from pathlib import Path

import pytest

from tests.fixtures import FixturePaths
from tests.fixtures import paths


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.joinpath("fixtures")


@pytest.fixture
def fixture_paths() -> FixturePaths:
    return paths
