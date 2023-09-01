# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests
from datadog_test_libs.utils.mock_dns import mock_local

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor

from .common import HERE, HOST, HOSTNAME_TO_PORT_MAPPING, INSTANCE_STANDALONE


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, 'docker', 'docker-compose.yaml'),
        build=True,
        conditions=[
            CheckEndpoints(
                [
                    'http://{}:4040/api/v1/applications'.format(HOST),
                    'http://{}:4050/api/v1/applications'.format(HOST),
                    'http://{}:4050/metrics/json'.format(HOST),
                ]
            ),
            WaitFor(check_metrics_available, wait=5),
        ],
        attempts=2,
    ):
        yield INSTANCE_STANDALONE, {'custom_hosts': get_custom_hosts()}


def check_metrics_available():
    endpoint = 'http://{}:4050/metrics/json'.format(HOST)
    r = requests.get(endpoint)
    return r.text.count("driver.spark.streaming") >= 6


def get_custom_hosts():
    return [(host, '127.0.0.1') for host in HOSTNAME_TO_PORT_MAPPING]


@pytest.fixture(scope='session', autouse=True)
def mock_local_tls_dns():
    with mock_local(HOSTNAME_TO_PORT_MAPPING):
        yield
