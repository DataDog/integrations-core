# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {"min_collection_interval": 15.0, "MONITOR": True, "AUDIT_LOGS_DIR_PATH": "/var/audit"}


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
