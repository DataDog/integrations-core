# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from .common import HOST, PORT

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


@pytest.fixture(scope='session', autouse=True)
def dd_environment(instance):
    with docker_run(
        os.path.join(DOCKER_DIR, 'docker-compose.yaml'),
        endpoints=instance['prometheus_url'],
    ):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {
        'prometheus_url': 'http://{}:{}/_status/vars'.format(HOST, PORT),
    }
