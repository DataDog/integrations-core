# Copyright (C) 2025 Crest Data.
# All rights reserved

import pytest

INSTANCE = {
    "min_collection_interval": 1800,
}
INVALID_INSTANCE = {
    "collect_data": "alerts",
}


@pytest.fixture(scope='session')
def dd_environment():
    yield INSTANCE, {'docker_platform': 'windows'}


@pytest.fixture
def instance():
    return INSTANCE.copy()


@pytest.fixture
def invalid_instance():
    return INVALID_INSTANCE.copy()
