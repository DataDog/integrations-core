import os

import pytest

from datadog_checks.dev import docker_run
from .common import INSTANCES

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


@pytest.fixture(scope='session', autouse=True)
def spin_up_envoy():
    flavor = os.getenv('FLAVOR', 'default')

    with docker_run(
        os.path.join(DOCKER_DIR, flavor, 'docker-compose.yaml'),
        build=True,
        endpoints=INSTANCES['main']['stats_url']
    ):
        yield
