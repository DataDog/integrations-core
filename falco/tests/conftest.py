# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import COMPOSE_FILE, INSTANCE

# Needed to mount volume for logging
E2E_METADATA = {'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}


@pytest.fixture(scope='session')
def dd_environment():
    conditions = [
        CheckEndpoints(INSTANCE['openmetrics_endpoint'], attempts=3, wait=3),
    ]
    with docker_run(compose_file=COMPOSE_FILE, conditions=conditions):
        yield {'instances': [copy.deepcopy(INSTANCE)]}


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)
