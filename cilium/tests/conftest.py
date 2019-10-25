# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def agent_instance():
    return {'agent_endpoint': 'localhost:9090/metrics', 'tags': ['pod_test']}


@pytest.fixture
def operator_instance():
    return {'operator_endpoint': ' localhost:6942/metrics', 'tags': ['operator_test'], 'send_distribution_buckets': True}

@pytest.fixture
def both_instance():
    return {
        'agent_endpoint': 'localhost:9090/metrics',
        'operator_endpoint': ' localhost:6942/metrics',
    }


@pytest.fixture()
def mock_agent_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'agent_metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


@pytest.fixture()
def mock_operator_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'operator_metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield
