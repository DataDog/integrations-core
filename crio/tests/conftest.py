from copy import deepcopy

import pytest

INSTANCE = {'prometheus_url': 'http://localhost:10249/metrics'}


@pytest.fixture(scope="session")
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
