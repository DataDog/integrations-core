# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {
    'prometheus_endpoint': 'http://localhost:10055/metrics',
    'health_service_check': True,
    'tags': ['custom:tag'],
}


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
