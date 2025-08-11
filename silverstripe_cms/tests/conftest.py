# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run

from .common import COMPOSE, INSTANCE

E2E_METADATA = {
    'start_commands': [
        'apt update',
        'apt install -y --no-install-recommends build-essential python3-dev libpq-dev',
    ],
}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(COMPOSE, 'docker-compose.yaml')

    with docker_run(
        compose_file,
        log_patterns=[r'.*'],
        build=True,
        service_name='silverstripe',
        sleep=30,
    ):
        instance = INSTANCE.copy()
        yield instance, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
