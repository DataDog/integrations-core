# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {'server': 'localhost', 'username': 'admin', 'password': 'admin', 'site': 'test', 'app_pools': 'test'}


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE, {'docker_platform': 'windows'}
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
