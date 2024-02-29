# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

URL = 'http://localhost:5000/metrics'


@pytest.fixture(scope='session')
def dd_environment():
    yield instance_v1()


@pytest.fixture
def instance_v1():
    return {'prometheus_url': URL}


@pytest.fixture
def instance_v2():
    return {'openmetrics_endpoint': URL}


@pytest.fixture()
def mock_metrics_endpoint():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield
