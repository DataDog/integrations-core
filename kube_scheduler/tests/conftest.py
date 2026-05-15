# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from unittest import mock

import pytest

INSTANCE = {
    'prometheus_url': 'http://localhost:10251/metrics',
    'send_histograms_buckets': True,
}


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture
def mock_healthcheck_wrapper():
    # _healthcheck_http_handler builds its own RequestsWrapper outside self.http
    with mock.patch('datadog_checks.kube_scheduler.kube_scheduler.RequestsWrapper'):
        yield
