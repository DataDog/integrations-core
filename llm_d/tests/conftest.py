# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import (
    COMPOSE_FILE,
    MOCKED_COORDINATOR_INSTANCE,
    MOCKED_ROUTER_INSTANCE,
    MOCKED_SIDECAR_INSTANCE,
)

INSTANCES = [
    MOCKED_ROUTER_INSTANCE,
    MOCKED_SIDECAR_INSTANCE,
    MOCKED_COORDINATOR_INSTANCE,
]


@pytest.fixture(scope='session')
def dd_environment():
    conditions = [CheckDockerLogs(identifier='caddy', patterns=['server running'])]
    conditions.extend(CheckEndpoints(instance['openmetrics_endpoint']) for instance in INSTANCES)
    with docker_run(COMPOSE_FILE, conditions=conditions):
        yield {'instances': INSTANCES}


@pytest.fixture
def instances():
    return copy.deepcopy(INSTANCES)


@pytest.fixture
def router_instance():
    return copy.deepcopy(MOCKED_ROUTER_INSTANCE)
