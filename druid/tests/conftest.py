# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import BROKER_URL, COORDINATOR_URL

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    """
    Start a standalone postgres server requiring authentication.
    """
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[
            CheckEndpoints(COORDINATOR_URL + '/status', attempts=200),
            CheckEndpoints(BROKER_URL + '/status', attempts=200),
        ],
    ):
        yield e2e_instance


@pytest.fixture(scope='session')
def instance():
    return {'process_url': BROKER_URL}


@pytest.fixture(scope='session')
def e2e_instance():
    return {'process_url': BROKER_URL}
