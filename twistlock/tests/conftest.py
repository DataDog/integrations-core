# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {
    'username': 'admin',
    'password': 'password',
    'url': 'http://localhost:8081',
    'tags': ["custom:tag"],
    'ssl_verify': False,
}


@pytest.fixture(scope="session")
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
