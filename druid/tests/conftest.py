# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.base.utils.http_testing import mock_http  # noqa: F401
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import BROKER_URL, COORDINATOR_URL

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope='session')
def dd_environment(instance):
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[
            CheckEndpoints(COORDINATOR_URL + '/status', attempts=100),
            CheckEndpoints(BROKER_URL + '/status', attempts=100),
        ],
    ):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {'url': BROKER_URL}
