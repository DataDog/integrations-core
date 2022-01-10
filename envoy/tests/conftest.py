import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.envoy import Envoy

from .common import DEFAULT_INSTANCE, DOCKER_DIR, ENVOY_LEGACY, FIXTURE_DIR, URL
from .legacy.common import FLAVOR, INSTANCES


@pytest.fixture(scope='session')
def fixture_path():
    yield lambda name: os.path.join(FIXTURE_DIR, name)


@pytest.fixture(scope='session')
def dd_environment():
    if ENVOY_LEGACY == 'true':
        instance = INSTANCES['main']
    else:
        instance = DEFAULT_INSTANCE

    with docker_run(
        os.path.join(DOCKER_DIR, FLAVOR, 'docker-compose.yaml'),
        build=True,
        endpoints="{}/stats".format(URL),
        log_patterns=['all dependencies initialized. starting workers'],
    ):
        yield instance


@pytest.fixture
def check():
    return lambda instance: Envoy('envoy', {}, [instance])
