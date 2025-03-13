# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run

from .common import COMPOSE, INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(COMPOSE, 'docker-compose.yaml')

    with docker_run(
        compose_file,
        build=True,
        sleep=30,
    ):
        instance = INSTANCE.copy()
        yield instance


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)