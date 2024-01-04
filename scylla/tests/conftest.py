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
def dd_environment(instance):
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file, log_patterns=[r'init - Scylla version \S* initialization completed.']):
        instances = {'instances': [instance]}
        yield instances


@pytest.fixture(scope="session")
def instance_legacy():
    return {'prometheus_url': INSTANCE_URL, 'tags': ['prometheus:true']}


@pytest.fixture(scope="session")
def instance():
    return {'openmetrics_endpoint': INSTANCE_URL, 'tags': ['prometheus:false']}


@pytest.fixture()
def mock_db_data():
    if os.environ['SCYLLA_VERSION'].startswith('5.'):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'scylla_5_metrics.txt')
    elif os.environ['SCYLLA_VERSION'].startswith('3.3'):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'scylla_3_3_metrics.txt')
    elif os.environ['SCYLLA_VERSION'].startswith('3.1'):
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
