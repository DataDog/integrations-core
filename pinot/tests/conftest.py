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

HERE = get_here()
HOST = get_docker_hostname()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

E2E_CONTROLLER_METRICS_URL = f'http://{HOST}:18009/metrics'
E2E_SERVER_METRICS_URL = f'http://{HOST}:18008/metrics'
E2E_BROKER_METRICS_URL = f'http://{HOST}:18007/metrics'
E2E_MINION_METRICS_URL = f'http://{HOST}:18006/metrics'

E2E_METRICS_URLS = [
    E2E_CONTROLLER_METRICS_URL,
    E2E_SERVER_METRICS_URL,
    E2E_BROKER_METRICS_URL,
    E2E_MINION_METRICS_URL,
]

E2E_INSTANCE = {
    'controller_endpoint': E2E_CONTROLLER_METRICS_URL,
    'server_endpoint': E2E_SERVER_METRICS_URL,
    'broker_endpoint': E2E_BROKER_METRICS_URL,
    'minion_endpoint': E2E_MINION_METRICS_URL,
    'tags': ['test:e2e'],
}


@pytest.fixture(scope='session')
def dd_environment():
    conditions = [
        CheckDockerLogs(
            COMPOSE_FILE,
            'Bootstrap complete: baseballStats table and segments loaded',
            attempts=180,
            service='pinot-bootstrap',
        ),
        CheckEndpoints(E2E_METRICS_URLS),
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
