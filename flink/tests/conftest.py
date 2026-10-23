# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_e2e_discovery_metadata, get_here
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.flink import FlinkCheck

JOBMANAGER_PORT = 9249
TASKMANAGER_PORT = 9250


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file=compose_file,
        conditions=(
            CheckEndpoints(f"http://{get_docker_hostname()}:{JOBMANAGER_PORT}/metrics"),
            CheckEndpoints(f"http://{get_docker_hostname()}:{TASKMANAGER_PORT}/metrics"),
        ),
        sleep=15,
    ):
        yield (
            {
                "openmetrics_endpoint": f"http://{get_docker_hostname()}:{JOBMANAGER_PORT}/metrics",
            },
            get_e2e_discovery_metadata(),
        )


@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": "http://localhost:9249/metrics",
    }


@pytest.fixture
def check(instance):
    return FlinkCheck('flink', {}, [copy.deepcopy(instance)])


@pytest.fixture()
def mock_metrics(fake_http, fake_http_response, instance):
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    fake_http_response(instance['openmetrics_endpoint'], text_data, headers={'Content-Type': 'text/plain'})
    yield
    fake_http.assert_all_responses_consumed()
    assert [(request.method, request.url) for request in fake_http.requests] == [
        ('GET', instance['openmetrics_endpoint'])
    ]
