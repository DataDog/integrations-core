# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.docker import ComposeFileDown
from datadog_checks.dev.structures import LazyFunction
from datadog_checks.dev.subprocess import run_command

from . import common


class IoTEdgeDown(LazyFunction):
    def __init__(self, compose_file):
        # type: (str) -> None
        self._compose_file_down = ComposeFileDown(compose_file)

    def __call__(self):
        # type: () -> None
        # The device container spawns these containers by interacting with the Docker runtime,
        # and they're not removed by the usual ComposeDown since they were not spawned via Docker Compose.
        # Stop them first so that networks are freed up and `docker-compose down` can remove them.
        run_command(['docker', 'stop', 'edgeHub', 'SimulatedTemperatureSensor'], check=True)

        self._compose_file_down()


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')

    conditions = [
        CheckDockerLogs(compose_file, 'Starting Azure IoT Edge Security Daemon', wait=5),
        CheckDockerLogs(compose_file, 'Successfully started module edgeAgent', wait=5),
        CheckDockerLogs(compose_file, r'[mgmt] .* 200 OK', wait=5),  # Verify any connectivity issues.
        CheckDockerLogs(compose_file, 'Successfully started module edgeHub', wait=5),
        CheckDockerLogs(compose_file, 'Successfully started module SimulatedTemperatureSensor', wait=5),
    ]

    env_vars = {
        "IOT_EDGE_LIBIOTHSM_STD_URL": common.IOT_EDGE_LIBIOTHSM_STD_URL,
        "IOT_EDGE_IOTEDGE_URL": common.IOT_EDGE_IOTEDGE_URL,
        "IOT_EDGE_AGENT_IMAGE": common.IOT_EDGE_AGENT_IMAGE,
        "IOT_EDGE_DEVICE_CONNECTION_STRING": common.IOT_EDGE_DEVICE_CONNECTION_STRING,
    }

    down = IoTEdgeDown(compose_file)

    with docker_run(compose_file, conditions=conditions, env_vars=env_vars, down=down):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {
        'edge_hub': {
            'prometheus_url': 'http://localhost:9601/metrics',
        },
        'edge_agent': {
            'prometheus_url': 'http://localhost:9602/metrics',
        },
        'tags': ['env:testing'],
    }
