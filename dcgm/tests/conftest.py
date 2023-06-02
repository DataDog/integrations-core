# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


## Fixtures that will be included in a conftest.py folder:
@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.INSTANCE],
        }


@pytest.fixture
def instance():
    return common.INSTANCE
