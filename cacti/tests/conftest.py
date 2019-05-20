# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import docker
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.subprocess import run_command
from datadog_checks.cacti import CactiCheck

from .common import (
    HERE,
    HOST,
    INSTANCE_INTEGRATION
)


@pytest.fixture(scope="session")
def dd_environment():
    env = {'HOST': HOST}
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        env_vars=env,
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    container = _get_container()
    commands = ["apt-get update",
                "apt-get install rrdtool librrd-dev libpython-dev build-essential -y",
                "pip install rrdtool"]
    for command in commands:
        exit_code, output = container.exec_run(command)
        if exit_code != 0:
            raise Exception(output)
    return CactiCheck('mapreduce', {}, {})


def _get_container():
    docker_ps = [
        'docker',
        'ps',
        '-aqf',
        ''"name=dd_cacti_py.*"''
    ]
    container_id = run_command(docker_ps, capture='out', check=True).stdout.rstrip()
    client = docker.client.from_env()
    return client.containers.get(container_id)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
