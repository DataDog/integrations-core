# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.azure_iot_edge.types import Instance
from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

from . import common, e2e_utils


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    if not common.E2E_IOT_EDGE_CONNSTR:
        raise RuntimeError("IOT_EDGE_CONNSTR must be set to start or stop the E2E environment.")

    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')

    conditions = [
        CheckDockerLogs(compose_file, r'[mgmt] .* 200 OK', wait=5),  # Verify any connectivity issues.
        CheckDockerLogs(compose_file, 'Successfully started module edgeAgent', wait=5),
        CheckDockerLogs(compose_file, 'Successfully started module edgeHub', wait=5),
        CheckDockerLogs(compose_file, 'Successfully started module SimulatedTemperatureSensor', wait=5),
        WaitFor(e2e_utils.edge_hub_endpoint_ready),
        WaitFor(e2e_utils.edge_agent_endpoint_ready),
    ]

    env_vars = {
        "E2E_LIBIOTHSM_STD_URL": common.E2E_LIBIOTHSM_STD_URL,
        "E2E_IOTEDGE_URL": common.E2E_IOTEDGE_URL,
        "E2E_IMAGE": common.E2E_IMAGE,
        "E2E_IOT_EDGE_CONNSTR": common.E2E_IOT_EDGE_CONNSTR,
    }

    up = e2e_utils.IoTEdgeUp(compose_file, network_name=common.E2E_NETWORK)
    down = e2e_utils.IoTEdgeDown(compose_file, stop_extra_containers=common.E2E_EXTRA_SPAWNED_CONTAINERS)

    with docker_run(conditions=conditions, env_vars=env_vars, up=up, down=down):
        yield e2e_instance, common.E2E_METADATA


@pytest.fixture(scope='session')
def e2e_instance():
    # type: () -> Instance
    return {
        'edge_hub_prometheus_url': common.E2E_EDGE_HUB_PROMETHEUS_URL,
        'edge_agent_prometheus_url': common.E2E_EDGE_AGENT_PROMETHEUS_URL,
        'security_daemon_management_api_url': common.E2E_SECURITY_DAEMON_MANAGEMENT_API_URL,
        'tags': common.CUSTOM_TAGS,
    }


@pytest.fixture(scope='session')
def mock_server():
    if Platform.is_windows():
        compose_filename = 'docker-compose-windows.yaml'
    else:
        compose_filename = 'docker-compose.yaml'

    compose_file = os.path.join(common.HERE, 'compose', 'mock_server', compose_filename)
    env_vars = {"MOCK_SERVER_PORT": str(common.MOCK_SERVER_PORT)}

    with docker_run(compose_file, env_vars=env_vars):
        yield


@pytest.fixture(scope='session')
def mock_instance():
    # type: () -> Instance
    return {
        'edge_hub_prometheus_url': common.MOCK_EDGE_HUB_PROMETHEUS_URL,
        'edge_agent_prometheus_url': common.MOCK_EDGE_AGENT_PROMETHEUS_URL,
        'security_daemon_management_api_url': common.MOCK_SECURITY_DAEMON_MANAGEMENT_API_URL,
        'tags': common.CUSTOM_TAGS,
    }
