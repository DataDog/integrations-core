# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {
    'host': 'foo',
    'kube_state_url': 'http://example.com:8080/metrics',
    'health_service_check': True,
    'tags': ['optional:tag1'],
    'telemetry': False,
}


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
