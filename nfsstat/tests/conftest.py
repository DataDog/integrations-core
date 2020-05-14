# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(common.COMPOSE_FILE, log_patterns=['mount.nfs: trying text-based options']):
        yield common.CONFIG
