# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from .common import FIXTURE_DIR

INSTANCE = {'prometheus_url': 'http://localhost:7979/metrics', 'tags': ['custom:tag']}


@pytest.fixture
def mock_external_dns(fake_http, fake_http_response):
    f_name = os.path.join(FIXTURE_DIR, 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()

    fake_http_response(INSTANCE['prometheus_url'], text_data, headers={'Content-Type': 'text/plain'})
    yield
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', INSTANCE['prometheus_url'])]


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
