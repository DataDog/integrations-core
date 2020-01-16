# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckCommandOutput
from datadog_checks.utils.common import get_docker_hostname

from .common import INSTANCE_DEFAULT_METRICS, MANAGER_DEFAULT_METRICS

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
INSTANCE_PORT = 9180
MANAGER_PORT = 56090
INSTANCE_URL = "http://{}:{}/metrics".format(HOST, INSTANCE_PORT)
MANAGER_URL = "http://{}:{}/metrics".format(HOST, MANAGER_PORT)


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        log_patterns=['JMX is enabled to receive remote connections'],
    ):

        init = CheckCommandOutput(
            'docker exec -u 0 scylla-manager sctool cluster add --host scylla-db', '.*-.*-.*-.*-.*'
        )
        if init():
            pass

        instances = {
            'instances': [
                {'instance_endpoint': INSTANCE_URL, 'metrics': INSTANCE_DEFAULT_METRICS},
                {'manager_endpoint': MANAGER_URL, 'metrics': MANAGER_DEFAULT_METRICS},
            ]
        }

        yield instances


@pytest.fixture(scope="session")
def db_instance():
    return {'instance_endpoint': INSTANCE_URL, 'tags': ['instance_test']}


@pytest.fixture
def manager_instance():
    return {'manager_endpoint': MANAGER_URL, 'tags': ['manager_test']}


@pytest.fixture()
def mock_db_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'scylla_metrics.txt')
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
def mock_manager_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'scylla_manager_metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield
