import os

import pytest

from datadog_checks.dev import docker_run

from .common import DOCKER_DIR, FIXTURE_DIR, FLAVOR, INSTANCES


@pytest.fixture(scope='session')
def fixture_path():
    yield lambda name: os.path.join(FIXTURE_DIR, name)


@pytest.fixture(scope='session')
def dd_environment():
    instance = INSTANCES['main']

    with docker_run(
        os.path.join(DOCKER_DIR, FLAVOR, 'docker-compose.yaml'),
        build=True,
        endpoints=instance['stats_url'],
        log_patterns=['all dependencies initialized. starting workers'],
    ):
        yield instance
