# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

INSTANCE = {'prometheus_url': 'http://localhost:5000/metrics'}


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture()
def mock_metrics_endpoint(fake_http, fake_http_response):
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'rb') as f:
        content = f.read()
    # test_check runs the check twice
    for _ in range(2):
        fake_http_response(INSTANCE['prometheus_url'], content, headers={'Content-Type': 'text/plain'})
    yield
    fake_http.assert_all_responses_consumed()
