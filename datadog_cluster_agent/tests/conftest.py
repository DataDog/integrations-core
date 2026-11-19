# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock
import pytest

INSTANCE = {'prometheus_url': 'http://localhost:5000/metrics'}


@pytest.fixture(scope='session')
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


def mock_metrics_response(text_data):
    return mock.patch(
        'requests.Session.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    )


@pytest.fixture(scope='session')
def metrics_text():
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt'), 'r') as f:
        return f.read()


@pytest.fixture()
def mock_metrics_endpoint(metrics_text):
    with mock_metrics_response(metrics_text):
        yield
