# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from datadog_test_libs.utils.mock_dns import mock_local

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor

from .common import HERE, HOST, HOSTNAME_TO_PORT_MAPPING, INSTANCE_STANDALONE


def read_url(url: str) -> bytes:
    try:
        with urlopen(url) as response:
            return response.read()
    except HTTPError as e:
        with e:
            return e.read()


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
            WaitFor(check_executors_registered, wait=5, attempts=60),
        ],
        attempts=2,
    ):
        yield INSTANCE_STANDALONE, {'custom_hosts': get_custom_hosts()}


def check_metrics_available():
    endpoint = 'http://{}:4050/metrics/json'.format(HOST)
    return read_url(endpoint).decode('utf-8').count("driver.spark.streaming") >= 6


def check_executors_registered():
    # Spark standalone executors are separate JVMs spawned by workers; they take time
    # to register with the driver after the application starts. Until at least one
    # non-driver executor appears, the /executors endpoint returns only the driver and
    # `spark.executor.*` metrics are never emitted, causing flaky integration tests.
    # The cluster runs a single worker with one core (SPARK_WORKER_CORES=1), so only one
    # of the two apps can own a non-driver executor at a time; either app having one is
    # enough for `test_integration_standalone` to observe executor metrics.
    for port in (4040, 4050):
        apps = json.loads(read_url('http://{}:{}/api/v1/applications'.format(HOST, port)).decode('utf-8'))
        if not apps:
            continue
        app_id = apps[0]['id']
        executors = json.loads(
            read_url('http://{}:{}/api/v1/applications/{}/executors'.format(HOST, port, app_id)).decode('utf-8')
        )
        if any(executor.get('id') != 'driver' for executor in executors):
            return True
    return False


def get_custom_hosts():
    return [(host, '127.0.0.1') for host in HOSTNAME_TO_PORT_MAPPING]


@pytest.fixture(scope='session', autouse=True)
def mock_local_tls_dns():
    with mock_local(HOSTNAME_TO_PORT_MAPPING):
        yield
