import pytest

from datadog_checks.dev import docker_run

from .common import COMPOSE_FILE, INSTANCE

# Needed to mount volume for logging
E2E_METADATA = {'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}


@pytest.fixture(scope='session')
def dd_environment():

    with docker_run(compose_file=COMPOSE_FILE):
        yield INSTANCE
