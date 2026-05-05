# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE

    with docker_run(
        compose_file,
        conditions=[
            CheckDockerLogs(compose_file, 'Ready to accept connections tcp', service='redis-standalone'),
            CheckEndpoints(common.MOCKED_INSTANCE['openmetrics_endpoint']),
        ],
    ):
        yield common.MOCKED_INSTANCE


@pytest.fixture(scope='session')
def instance():
    return copy.deepcopy(common.MOCKED_INSTANCE)
