# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckEndpoints

INSTANCE = {"service": "server"}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), "compose", "docker-compose.yaml")

    with docker_run(
        compose_file=compose_file,
        conditions=[CheckEndpoints(f"http://{get_docker_hostname()}:8000/metrics")],
    ):
        yield copy.deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)
