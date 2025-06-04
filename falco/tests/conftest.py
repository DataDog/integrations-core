import os
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.falco import FalcoCheck

from .common import DEFAULT_INSTANCE, COMPOSE_FILE, HOST, URL


# Needed to mount volume for logging
E2E_METADATA = {'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}

@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        COMPOSE_FILE,
        endpoints="{}/metrics".format(URL),
    ):
        yield DEFAULT_INSTANCE


@pytest.fixture(scope='session')
def instance():
    return {'openmetrics_endpoint': '{}/metrics'.format(URL)}
