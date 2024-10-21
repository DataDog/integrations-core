# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run, get_here

from .common import INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
    with docker_run(compose_file, sleep=5):
        yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture
def metrics_path():
    return os.path.join(get_here(), "fixtures", "metrics.txt")
