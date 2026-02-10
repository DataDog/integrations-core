# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import (
    BROKER_INSTANCE,
    CONTROLLER_INSTANCE,
    MINION_INSTANCE,
    SERVER_INSTANCE,
)

# E2E test configuration
HERE = get_here()
HOST = get_docker_hostname()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

# Port for JMX Prometheus exporter metrics endpoint
# In QuickStart mode, all components share a single JVM and metrics endpoint
# Using 18009 to avoid conflicts with common local ports
E2E_METRICS_PORT = 18009
E2E_METRICS_URL = f'http://{HOST}:{E2E_METRICS_PORT}/metrics'

E2E_INSTANCE = {
    'controller_endpoint': E2E_METRICS_URL,
    'tags': ['test:e2e'],
}


@pytest.fixture(scope='session')
def dd_environment():
    conditions = [
        # Wait for Pinot QuickStart tables to be created (indicates cluster is ready)
        CheckDockerLogs('pinot', 'TableConfigs baseballStats successfully added', attempts=60),
        # Wait for metrics endpoint to be available
        CheckEndpoints([E2E_METRICS_URL]),
    ]

    with docker_run(COMPOSE_FILE, conditions=conditions, sleep=5, attempts=2):
        yield E2E_INSTANCE


@pytest.fixture
def instance():
    return copy.deepcopy(CONTROLLER_INSTANCE)


@pytest.fixture
def controller_instance():
    return copy.deepcopy(CONTROLLER_INSTANCE)


@pytest.fixture
def server_instance():
    return copy.deepcopy(SERVER_INSTANCE)


@pytest.fixture
def broker_instance():
    return copy.deepcopy(BROKER_INSTANCE)


@pytest.fixture
def minion_instance():
    return copy.deepcopy(MINION_INSTANCE)


@pytest.fixture
def e2e_instance():
    return copy.deepcopy(E2E_INSTANCE)
