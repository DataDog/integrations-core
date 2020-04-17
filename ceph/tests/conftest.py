# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import time

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.subprocess import run_command

from .common import BASIC_CONFIG, HERE

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y docker.io',
    ],
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
}


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    # We need a custom condition to wait a bit longer
    with docker_run(
        compose_file=compose_file,
        conditions=[
            CheckDockerLogs(compose_file, 'spawning ceph --cluster ceph -w', wait=5),
            CheckDockerLogs(compose_file, 'Running on http://0.0.0.0:5000/')
        ],
    ):
        # Clean the disk space warning
        run_command(
            ['docker', 'exec', 'dd-test-ceph', 'ceph', 'tell', 'mon.*', 'injectargs', '--mon_data_avail_warn', '5']
        )
        # Wait a bit for the change to take effect
        condition = CheckDockerLogs(compose_file, 'Cluster is now healthy')
        condition()
        yield BASIC_CONFIG, E2E_METADATA
