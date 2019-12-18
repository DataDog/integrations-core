# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        endpoints=['http://{}:{}'.format(common.HOST, common.HTTP_START_PORT + i) for i in range(6)],
        sleep=10,
    ):
        yield common.CONFIG


@pytest.fixture
def instance():
    return deepcopy(common.CONFIG)
