# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {"min_collection_interval": 50.0, "MONITOR": True, "IP": "10.10.10.10", "PORT": 15423}


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
