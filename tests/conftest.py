import pytest
from faker import Faker

from asynction.types import Info
from tests.fixtures import FixturePaths
from tests.fixtures import paths


@pytest.fixture
def fixture_paths() -> FixturePaths:
    return paths


@pytest.fixture
def faker() -> Faker:
    return Faker()


@pytest.fixture
def server_info(faker: Faker) -> Info:
    return Info(
        title=faker.word(),
        version=faker.pystr(),
        description=faker.sentence(),
    )
