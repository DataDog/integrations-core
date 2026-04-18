# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse

from .common import FIXTURE_DIR

INSTANCE = {'prometheus_url': 'http://localhost:7979/metrics', 'tags': ['custom:tag']}


@pytest.fixture
def mock_external_dns(mock_http):
    f_name = os.path.join(FIXTURE_DIR, 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()

    mock_http.get.return_value = MockHTTPResponse(content=text_data, headers={'Content-Type': 'text/plain'})
    yield


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
