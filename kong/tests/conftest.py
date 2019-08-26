import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.kong import Kong

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a kong cluster
    """
    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'docker-compose.yml'), endpoints=common.STATUS_URL
    ):
        yield common.instance_1


@pytest.fixture
def check():
    return Kong(common.CHECK_NAME, {}, {})
