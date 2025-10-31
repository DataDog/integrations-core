# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {
    "min_collection_interval": 15,
    "package_ecosystem": "pypi",
    "dependency_file_path": "/opt/test/logs/requirements.txt",
}


@pytest.fixture
def example_dependencies():
    return "flask\nrequests\npandas"


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
