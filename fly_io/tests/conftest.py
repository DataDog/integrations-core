# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

INSTANCE = {'openmetrics_endpoint': 'http://localhost:8080/metrics'}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(INSTANCE["openmetrics_endpoint"]),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [INSTANCE],
        }


@pytest.fixture
def instance():
    return INSTANCE
