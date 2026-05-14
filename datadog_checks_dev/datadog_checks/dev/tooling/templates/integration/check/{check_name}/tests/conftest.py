{license_header}
from typing import Iterator

import pytest

from datadog_checks.base.types import InstanceType


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[None]:
    yield


@pytest.fixture
def instance() -> InstanceType:
    return {{}}
