# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from datadog_checks.dev.docker import ComposeFileDown, ComposeFileUp
from datadog_checks.dev.structures import LazyFunction
from datadog_checks.dev.subprocess import run_command

from . import common


class IoTEdgeUp(LazyFunction):
    def __init__(self, compose_file, network_name):
        # type: (str, str) -> None
        self._compose_file_up = ComposeFileUp(compose_file)
        self._network_name = network_name

    def __call__(self):
        # type: () -> Any
        result = run_command(['docker', 'network', 'inspect', self._network_name], capture=True)
        network_exists = result.code == 0
        if not network_exists:
            run_command(['docker', 'network', 'create', self._network_name], check=True)

        return self._compose_file_up()


class IoTEdgeDown(LazyFunction):
    def __init__(self, compose_file, stop_extra_containers):
        # type: (str, list) -> None
        self._compose_file_down = ComposeFileDown(compose_file)
        self._stop_extra_containers = stop_extra_containers

    def __call__(self):
        # type: () -> Any
        run_command(['docker', 'stop'] + self._stop_extra_containers, check=True)
        return self._compose_file_down()


def edge_hub_endpoint_ready():
    # type: () -> bool
    try:
        response = requests.get(common.EDGE_HUB_PROMETHEUS_URL)
        response.raise_for_status()
    except requests.HTTPError:
        return False

    # Not all metrics are available right away, wait for one known such metric to be returned.
    return response.status_code == 200 and "edgehub_queue_length{" in response.text


def edge_agent_endpoint_ready():
    # type: () -> bool
    try:
        response = requests.get(common.EDGE_AGENT_PROMETHEUS_URL)
        response.raise_for_status()
    except requests.HTTPError:
        return False

    # Not all metrics are available right away, wait for one known such metric to be returned.
    return response.status_code == 200 and "total_network_out_bytes{" in response.text


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')

    conditions = [
        CheckDockerLogs(compose_file, r'[mgmt] .* 200 OK', wait=5),  # Verify any connectivity issues.
        CheckDockerLogs(compose_file, 'Successfully started module edgeAgent', wait=5),
        CheckDockerLogs(compose_file, 'Successfully started module edgeHub', wait=5),
        CheckDockerLogs(compose_file, 'Successfully started module SimulatedTemperatureSensor', wait=5),
        WaitFor(edge_hub_endpoint_ready),
        WaitFor(edge_agent_endpoint_ready),
    ]

    env_vars = {
        "IOT_EDGE_LIBIOTHSM_STD_URL": common.IOT_EDGE_LIBIOTHSM_STD_URL,
        "IOT_EDGE_IOTEDGE_URL": common.IOT_EDGE_IOTEDGE_URL,
        "IOT_EDGE_AGENT_IMAGE": common.IOT_EDGE_AGENT_IMAGE,
        "IOT_EDGE_DEVICE_CONNECTION_STRING": common.IOT_EDGE_DEVICE_CONNECTION_STRING,
    }

    up = IoTEdgeUp(compose_file, network_name=common.IOT_EDGE_NETWORK)
    down = IoTEdgeDown(compose_file, stop_extra_containers=common.EDGE_AGENT_SPAWNED_CONTAINERS)

    with docker_run(conditions=conditions, env_vars=env_vars, up=up, down=down):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {
        'edge_hub': {
            'prometheus_url': common.EDGE_HUB_PROMETHEUS_URL,
        },
        'edge_agent': {
            'prometheus_url': common.EDGE_AGENT_PROMETHEUS_URL,
        },
        'tags': common.CUSTOM_TAGS,
    }
