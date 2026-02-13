# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {
    "api_key": "test_api_key_12345",
    "ip_addresses": ["192.168.1.1", "10.0.0.1"],
    "max_age_in_days": 90,
    "min_collection_interval": 3600,
}

CONFIG = {"instances": [INSTANCE], "init_config": {}}


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture
def config():
    return deepcopy(CONFIG)
