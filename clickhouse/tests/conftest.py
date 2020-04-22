# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    ping_urls = ['http://{}:{}/ping'.format(common.HOST, common.HTTP_START_PORT + i) for i in range(6)]
    replica_status_urls = ['http://{}:{}/replicas_status'.format(common.HOST, common.HTTP_START_PORT + i) for i in range(6)]
    with docker_run(
        common.COMPOSE_FILE,
        endpoints=ping_urls + replica_status_urls,
    ):
        yield common.CONFIG


@pytest.fixture
def instance():
    return deepcopy(common.CONFIG)
