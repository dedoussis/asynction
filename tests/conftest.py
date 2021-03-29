import pytest
from faker import Faker

from tests.fixtures import FixturePaths
from tests.fixtures import paths


@pytest.fixture
def fixture_paths() -> FixturePaths:
    return paths


@pytest.fixture
def faker() -> Faker:
    return Faker()
