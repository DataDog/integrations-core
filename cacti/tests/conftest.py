# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import docker
import pytest

from datadog_checks.cacti import CactiCheck
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.structures import TempDir

from .common import E2E_METADATA, HERE, HOST, INSTANCE_INTEGRATION, RRD_PATH


def set_up_cacti():
    client = docker.client.from_env()
    container = client.containers.get("dd-test-cacti")
    if not container:
        raise Exception("Could not find container")

    commands = ['/sbin/restore', 'mysql -u root -e "flush privileges;"', 'php /opt/cacti/lib/poller.php --force']
    for command in commands:
        code, out = container.exec_run(command)
        print(command)
        print(out)
        if code != 0:
            raise Exception(out)
    return True


@pytest.fixture(scope="session")
def dd_environment():
    with TempDir("nagios_var_log") as rrd_path:
        e2e_metadata = deepcopy(E2E_METADATA)
        e2e_metadata['docker_volumes'] = ['{}:{}'.format(rrd_path, RRD_PATH)]

        with docker_run(
            conditions=[WaitFor(set_up_cacti)],
            compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
            env_vars={'HOST': HOST, 'RRD_PATH': rrd_path},
        ):
            yield INSTANCE_INTEGRATION, e2e_metadata


@pytest.fixture
def check():
    return CactiCheck('cacti', {}, {})


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
