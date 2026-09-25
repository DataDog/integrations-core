# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from unittest import mock
from urllib.request import urlopen

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_e2e_discovery_metadata, get_here, run_command
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.flink import FlinkCheck

JOBMANAGER_PORT = 9249
TASKMANAGER_PORT = 9250


def _task_metrics_present():
    # Task/operator metric groups only exist once a job is actually scheduled
    # onto the TaskManager, which lags job submission by a few seconds.
    with urlopen(f"http://{get_docker_hostname()}:{TASKMANAGER_PORT}/metrics", timeout=5) as response:
        return b'flink_taskmanager_job_task_numRecordsIn' in response.read()


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file=compose_file,
        conditions=(
            CheckEndpoints(f"http://{get_docker_hostname()}:{JOBMANAGER_PORT}/metrics"),
            CheckEndpoints(f"http://{get_docker_hostname()}:{TASKMANAGER_PORT}/metrics"),
            lambda: run_command(
                [
                    'docker',
                    'exec',
                    'flink-jobmanager',
                    'flink',
                    'run',
                    '-d',
                    '/opt/flink/examples/streaming/StateMachineExample.jar',
                ],
                check=True,
            ),
            WaitFor(_task_metrics_present, attempts=30, wait=2),
        ),
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
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.Session.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"},
        ),
    ):
        yield
