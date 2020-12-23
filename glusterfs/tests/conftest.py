# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import time

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import docker_run, run_command

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
    with docker_run(compose_file=compose_file):
        create_volume()
        yield {'init_config': {'gstatus_path': '/opt/datadog-agent/embedded/sbin/gstatus'}}, E2E_METADATA


@pytest.fixture
def instance():
    return {}


@pytest.fixture()
def mock_gstatus_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'gstatus.json')
    with open(f_name) as f:
        data = f.read()
    with mock.patch('datadog_checks.glusterfs.check.get_subprocess_output', return_value=(data, '', 0)):
        yield


def create_volume():
    for command in (
        'gluster peer probe gluster-node-2',
        'mkdir /export',
        'gluster volume create gv0 gluster-node-1:/export force',
        'gluster volume start gv0',
    ):
        run_command("docker exec gluster-node-1 {}".format(command), capture=True, check=True)
        time.sleep(10)


