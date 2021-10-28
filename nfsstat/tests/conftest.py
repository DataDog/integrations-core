# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run

from .common import COMPOSE_FILE, CONFIG, E2E_METADATA


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(COMPOSE_FILE, log_patterns=['NFS Client ready.']):
        yield CONFIG, E2E_METADATA
