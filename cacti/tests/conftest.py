# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.cacti import CactiCheck
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from .common import E2E_METADATA, HERE, INSTANCE_INTEGRATION


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        conditions=[CheckDockerLogs('cacti', ['Starting httpd service.'], attempts=100, wait=3)],
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
    ):
        yield INSTANCE_INTEGRATION, E2E_METADATA


@pytest.fixture
def check():
    return CactiCheck('cacti', {}, [{}])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
