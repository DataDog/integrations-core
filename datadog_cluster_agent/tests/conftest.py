# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse

INSTANCE = {'prometheus_url': 'http://localhost:5000/metrics'}


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture()
def mock_metrics_endpoint(mock_http, mocker):
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mocker.patch(
        'datadog_checks.base.checks.openmetrics.mixins.OpenMetricsScraperMixin.get_http_handler',
        return_value=mock_http,
    )
    mock_http.get.return_value = MockHTTPResponse(content=text_data, headers={'Content-Type': 'text/plain'})
    yield
