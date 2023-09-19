# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import time

import mock
import pytest

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import WaitFor, docker_run, run_command

from .common import CONFIG, INSTANCE

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y docker.io',
    ],
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yaml')
    with docker_run(
        compose_file=compose_file,
        conditions=[WaitFor(create_volume)],
        down=delete_volume,
    ):
        yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def config():
    return copy.deepcopy(CONFIG)


@pytest.fixture()
def mock_gstatus_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'gstatus.json')
    with open(f_name) as f:
        data = f.read()
    with mock.patch('datadog_checks.glusterfs.check.get_subprocess_output', return_value=(data, '', 0)):
        yield


def create_volume():
    run_command("docker exec gluster-node-2 mkdir -p /export-test", capture=True, check=True)

    for command in (
        'gluster peer probe gluster-node-2',
        'mkdir -p /export-test',
        'gluster volume create gv0 replica 2 gluster-node-1:/export-test gluster-node-2:/export-test force',
        'gluster volume start gv0',
        'yum update -y',
        'yum install -y python3',
        'curl -LO https://github.com/gluster/gstatus/releases/download/v1.0.5/gstatus',
        'chmod +x ./gstatus',
        'mv ./gstatus /usr/local/bin/gstatus',
    ):
        run_command("docker exec gluster-node-1 {}".format(command), capture=True, check=True)
        time.sleep(10)


def delete_volume():
    run_command("docker exec gluster-node-1 gluster volume delete gv0", capture=True, check=True)
