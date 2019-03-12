import pytest
import os

from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a kong cluster
    """
    compose_directory = os.path.join(common.HERE, 'compose')

    with docker_run(
        compose_file=os.path.join(compose_directory, 'docker-compose.yml'),
        env_vars={'COMPOSE_DIRECTORY_PATH': compose_directory},
        endpoints=common.STATUS_URL
    ):
        yield common.instance_1
