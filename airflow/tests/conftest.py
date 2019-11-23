# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import URL

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope='session')
def dd_environment(instance):
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[
            CheckEndpoints(URL + '/api/experimental/test', attempts=100),
        ],
    ):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {'url': URL}
