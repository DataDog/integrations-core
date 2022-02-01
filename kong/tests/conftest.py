import os

import pytest

from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a kong cluster
    """
    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'docker-compose.yml'), endpoints=common.STATUS_URL
    ):
        yield common.openmetrics_instance


@pytest.fixture
def instance_openmetrics_v2():
    return common.openmetrics_instance
