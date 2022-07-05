# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run, get_here

from . import common

HERE = get_here()


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        endpoints=[
            'http://{}:80/api/v2/stats/system'.format(common.HOST),
        ],
    ):
        yield common.INSTANCE


@pytest.fixture
def instance():
    return common.INSTANCE
