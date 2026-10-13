# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock
import pytest

from datadog_checks.dev.http import MockResponse

INSTANCE = {'prometheus_url': 'http://localhost:5000/metrics'}


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture()
def mock_metrics_endpoint():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.Session.get',
        return_value=MockResponse(content=text_data, headers={'Content-Type': "text/plain"}),
    ):
        yield
