# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest
import docker

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.cacti import CactiCheck

from .common import (
    HERE,
    HOST,
    INSTANCE_INTEGRATION,
    E2E_METADATA
)


def create_db_user():
    client = docker.client.from_env()
    container = client.containers.get("dd-test-cacti")
    if not container:
        raise Exception("Could not find container")

    commands = [
        "CREATE USER 'cactiuser'@'localhost' IDENTIFIED BY 'cactipass';",
        "GRANT ALL PRIVILEGES ON *.* TO 'cactiuser'@'localhost' WITH GRANT OPTION;",
        "CREATE USER 'cactiuser'@'%' IDENTIFIED BY 'cactipass';"
        "GRANT ALL PRIVILEGES ON *.* TO 'cactiuser'@'%' WITH GRANT OPTION;",
    ]

    for command in commands:
        code, out = container.exec_run(
            'mysql -u root -D cacti -e "{}"'.format(command))
        if code is not 0:
            raise Exception(out)
    return True


@pytest.fixture(scope="session")
def dd_environment():
    env = {'HOST': HOST}
    with docker_run(
        conditions=[WaitFor(create_db_user)],
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        env_vars=env,
    ):
        yield INSTANCE_INTEGRATION, E2E_METADATA


@pytest.fixture
def check():
    return CactiCheck('cacti', {}, {})


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
