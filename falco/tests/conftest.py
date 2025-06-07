import pytest

from datadog_checks.dev import CheckDockerLogs, CheckEndpoints, docker_run

from .common import COMPOSE_FILE, INSTANCE_CONFIG, URL

# Needed to mount volume for logging
E2E_METADATA = {'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}


@pytest.fixture(scope='session')
def dd_environment():

    conditions = [
        CheckDockerLogs(COMPOSE_FILE, patterns='Falco version', wait=5),
        CheckDockerLogs(COMPOSE_FILE, patterns='Falco initialized with configuration files', wait=5),
        CheckEndpoints(URL, attempts=180, wait=3),
    ]

    with docker_run(
        compose_file=COMPOSE_FILE,
        conditions=conditions,
    ):
        yield INSTANCE_CONFIG
