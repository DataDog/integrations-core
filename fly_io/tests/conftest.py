# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import COMPOSE_FILE, INSTANCE, LAB_INSTANCE, USE_FLY_LAB


@pytest.fixture(scope='session')
def dd_environment():
    if not USE_FLY_LAB:
        compose_file = COMPOSE_FILE
        conditions = [
            CheckDockerLogs(identifier='caddy', patterns=['server running']),
            CheckEndpoints(INSTANCE["openmetrics_endpoint"]),
        ]
        with docker_run(compose_file, conditions=conditions):
            yield INSTANCE
    else:
        yield LAB_INSTANCE


@pytest.fixture
def instance():
    return INSTANCE
