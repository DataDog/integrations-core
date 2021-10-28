# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run

from .common import COMPOSE_FILE, CONFIG


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(COMPOSE_FILE, sleep=10):
        yield CONFIG['instances'][0]
