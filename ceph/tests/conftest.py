# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from .common import HERE, BASIC_CONFIG


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, "compose", "docker-compose.yaml")
    # We need a custom condition to wait a bit longer
    condition = CheckDockerLogs(compose_file, "spawning ceph --cluster ceph -w", wait=5)
    with docker_run(
        compose_file=compose_file, conditions=[condition],
        sleep=5,  # Let's wait just a little bit after ceph got spawned to remove flakyness
    ):
        yield BASIC_CONFIG, "local"
