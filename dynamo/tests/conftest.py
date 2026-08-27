# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import COMPOSE_FILE, MOCKED_FRONTEND_INSTANCE, MOCKED_WORKER_INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(MOCKED_FRONTEND_INSTANCE['openmetrics_endpoint']),
        CheckEndpoints(MOCKED_WORKER_INSTANCE['openmetrics_endpoint']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [MOCKED_FRONTEND_INSTANCE, MOCKED_WORKER_INSTANCE],
        }


@pytest.fixture
def frontend_instance():
    return copy.deepcopy(MOCKED_FRONTEND_INSTANCE)


@pytest.fixture
def worker_instance():
    return copy.deepcopy(MOCKED_WORKER_INSTANCE)
