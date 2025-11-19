# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import COMPOSE_FILE, MOCKED_INSTANCE, MOCKED_INSTANCE_RAY, MOCKED_VERSION_ENDPOINT


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(MOCKED_INSTANCE['openmetrics_endpoint']),
        CheckEndpoints(MOCKED_VERSION_ENDPOINT),
        CheckEndpoints(MOCKED_INSTANCE_RAY['openmetrics_endpoint']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [MOCKED_INSTANCE, MOCKED_INSTANCE_RAY],  # Include both instances
        }


@pytest.fixture
def instance():
    return copy.deepcopy(MOCKED_INSTANCE)


@pytest.fixture
def ray_instance():
    return copy.deepcopy(MOCKED_INSTANCE_RAY)
