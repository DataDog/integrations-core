# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run

from .common import COMPOSE_FILE, INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(COMPOSE_FILE, log_patterns=['traffic_server: using root directory']):
        yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE
