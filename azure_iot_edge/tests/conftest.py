# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.azure_iot_edge.types import Instance  # noqa: F401
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

from . import common, e2e_utils


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    if not common.E2E_IOT_EDGE_CONNSTR:
        raise RuntimeError("IOT_EDGE_CONNSTR must be set to start or stop the E2E environment.")

    if common.E2E_IOT_EDGE_TLS_ENABLED:
        compose_filename = 'docker-compose-tls.yaml'
    else:
        compose_filename = 'docker-compose.yaml'

    compose_file = os.path.join(common.HERE, 'compose', compose_filename)

    conditions = [
        CheckDockerLogs(compose_file, r'[mgmt] .* 200 OK', wait=5),  # Verify Security Manager boots.
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

    if common.E2E_IOT_EDGE_TLS_ENABLED:
        for path in (
            common.E2E_IOT_EDGE_DEVICE_CA_CERT,
            common.E2E_IOT_EDGE_DEVICE_CA_CERT,
            common.E2E_IOT_EDGE_DEVICE_CA_PK,
        ):
            if not os.path.exists(path):
                message = (
                    "Path {!r} does not exist. "
                    "Please follow instructions in azure_iot_edge/tests/tls/README.md to "
                    "configure test TLS certificates."
                ).format(path)
                raise RuntimeError(message)

        env_vars.update(
            {
                "E2E_IOT_EDGE_ROOT_CA_CERT": common.E2E_IOT_EDGE_ROOT_CA_CERT,
                "E2E_IOT_EDGE_DEVICE_CA_CERT": common.E2E_IOT_EDGE_DEVICE_CA_CERT,
                "E2E_IOT_EDGE_DEVICE_CA_PK": common.E2E_IOT_EDGE_DEVICE_CA_PK,
            }
        )

    up = e2e_utils.IoTEdgeUp(compose_file, network_name=common.E2E_NETWORK)
    down = e2e_utils.IoTEdgeDown(compose_file, stop_extra_containers=common.E2E_EXTRA_SPAWNED_CONTAINERS)

    with docker_run(conditions=conditions, env_vars=env_vars, up=up, down=down, sleep=10):
        yield e2e_instance, common.E2E_METADATA


@pytest.fixture(scope='session')
def e2e_instance():
    # type: () -> Instance
    return {
        'edge_hub_prometheus_url': common.E2E_EDGE_HUB_PROMETHEUS_URL,
        'edge_agent_prometheus_url': common.E2E_EDGE_AGENT_PROMETHEUS_URL,
        'tags': common.CUSTOM_TAGS,
    }


@pytest.fixture(scope='session')
def mock_server():
    compose_file = os.path.join(common.HERE, 'compose', 'mock_server', 'docker-compose.yaml')
    env_vars = {"MOCK_SERVER_PORT": str(common.MOCK_SERVER_PORT)}

    with docker_run(
        compose_file,
        endpoints=[
            common.MOCK_EDGE_HUB_PROMETHEUS_URL,
            common.MOCK_EDGE_AGENT_PROMETHEUS_URL,
        ],
        env_vars=env_vars,
    ):
        yield


@pytest.fixture(scope='session')
def mock_instance():
    # type: () -> Instance
    return {
        'edge_hub_prometheus_url': common.MOCK_EDGE_HUB_PROMETHEUS_URL,
        'edge_agent_prometheus_url': common.MOCK_EDGE_AGENT_PROMETHEUS_URL,
        'tags': common.CUSTOM_TAGS,
    }
