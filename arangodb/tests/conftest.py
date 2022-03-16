# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev import docker_run

from .common import HOST, PORT

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')
URL = 'http://{}:{}/_admin/metrics/v2'


@pytest.fixture(scope='session')
def dd_environment(instance):
    with docker_run(
        os.path.join(DOCKER_DIR, 'docker-compose.yaml'),
    ):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {
        'openmetrics_endpoint': URL.format(HOST, PORT),
        'username': 'root',
        'password': 'password',
        'tls_verify': False,
    }


@pytest.fixture()
def mock_agent_data():
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
