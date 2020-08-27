# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
INSTANCE_PORT = 9180
INSTANCE_URL = "http://{}:{}/metrics".format(HOST, INSTANCE_PORT)


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file, log_patterns=[r'init - Scylla version \S* initialization completed.']):
        instances = {'instances': [{'prometheus_url': INSTANCE_URL}]}
        yield instances


@pytest.fixture(scope="session")
def db_instance():
    return {'prometheus_url': INSTANCE_URL, 'tags': ['instance_test']}


@pytest.fixture()
def mock_db_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'scylla_metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"},
        ),
    ):
        yield
