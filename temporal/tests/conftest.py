# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run, get_here


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), "compose", "docker-compose.yaml")
    conditions = []

    with docker_run(
        compose_file=compose_file,
        conditions=conditions,
    ):
        yield {}


@pytest.fixture
def instance():
    return {}
