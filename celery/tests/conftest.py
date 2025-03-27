# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    """
    Start docker-compose environment before running tests and tear it down afterward.
    """
    compose_file = common.COMPOSE_FILE
    
    with docker_run(
        compose_file,
        conditions=[
            CheckDockerLogs('docker-redis-standalone-1', 'Ready to accept connections tcp'),
        ],
        env_vars={
            'DD_LOGS_ENABLED': 'true',
            'DD_CONTAINER_COLLECT_ALL': 'true',
        },
    ):
        yield {
            'instances': [common.MOCKED_INSTANCE]
        }

@pytest.fixture(scope='session')
def instance():
    """
    Return a default instance used for the integration.
    """
    return copy.deepcopy(common.MOCKED_INSTANCE)

