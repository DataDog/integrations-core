# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run

from .common import CHECK_NAME, HERE, INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file, sleep=60, mount_logs=True):
        yield INSTANCE


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)


@pytest.fixture
def check():
    # Lazily import to support E2E on Windows
    from datadog_checks.gearmand import Gearman

    return lambda instance: Gearman(CHECK_NAME, {}, [instance])
