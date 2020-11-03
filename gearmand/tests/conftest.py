# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run

from .common import CHECK_NAME, HERE, INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    with docker_run(compose_file, sleep=20, mount_logs=True):
        yield INSTANCE


@pytest.fixture
def check():
    # Lazily import to support E2E on Windows
    from datadog_checks.gearmand import Gearman

    return Gearman(CHECK_NAME, {}, {})
