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

INIT_CONFIG = {"guarddog_path": "/usr/local/bin/guarddog"}

CONFIG = {"instances": [INSTANCE], "init_config": INIT_CONFIG}


@pytest.fixture
def example_dependencies():
    return "flask\nrequests\npandas"


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture
def config():
    return deepcopy(CONFIG)
