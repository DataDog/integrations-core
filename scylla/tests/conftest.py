# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.utils.common import get_docker_hostname


HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
INSTANCE_PORT = 9180
MANAGER_PORT = 56090
INSTANCE_URL = "http://{}:{}/metrics".format(HOST, INSTANCE_PORT)
MANAGER_URL = "http://{}:{}/metrics".format(HOST, MANAGER_PORT)


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        log_patterns=['Starting Prometheus HTTP', 'Service started'],
    ):

        result = run_command('docker exec -u 0 scylla-manager sctool cluster add --host scylla-db', capture='both')

        CheckDockerLogs(compose_file, ['Adding new cluster', 'Task ended'])
        print(result)

        instances = {
            'instances': [
                {'instance_endpoint': INSTANCE_URL},
                {'manager_endpoint': MANAGER_URL},
            ]
        }

        yield instances


@pytest.fixture(scope="session")
def db_instance():
    return {'instance_endpoint': INSTANCE_URL, 'tags': ['instance_test']}


@pytest.fixture(scope="session")
def manager_instance():
    return {'manager_endpoint': MANAGER_URL, 'tags': ['manager_test']}


@pytest.fixture(scope="session")
def combined_instance():
    # should raise an error with this config
    return {'instance_endpoint': INSTANCE_URL, 'manager_endpoint': MANAGER_URL, 'tags': ['config_error_test']}


def mocked_metrics(endpoint):
    if endpoint == INSTANCE_URL:
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'scylla_metrics.txt')
        with open(f_name, 'r') as f:
            text_data = f.read()
            return text_data.split('\n')
    elif endpoint == MANAGER_URL:
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'scylla_manager_metrics.txt')
        with open(f_name, 'r') as f:
            text_data = f.read()
            return text_data.split('\n')


def mock_get(*args, **kwargs):
    url = args[0]
    data = mocked_metrics(url)

    return mock.MagicMock(
        status_code=200,
        raise_for_status=lambda **kargs: kwargs,
        iter_lines=lambda **kwargs: data,
        headers={'Content-Type': "text/plain"}
    )


@pytest.fixture()
def mock_metrics_request():
    with mock.patch('requests.get', new=mock_get):
        yield
