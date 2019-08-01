# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.ssh_tunnel import tcp_tunnel
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.dev.utils import get_here
from datadog_checks.oracle import Oracle

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_NAME = "oracle"


@pytest.fixture
def check():
    return Oracle(CHECK_NAME, {}, {})


@pytest.fixture
def instance():
    return {
        'server': 'localhost:1521',
        'user': 'system',
        'password': 'oracle',
        'service_name': 'xe',
        'tags': ['optional:tag1'],
    }


@pytest.fixture(scope='session')
def dd_environment():
    with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
        ip = outputs['ip']['value']
        private_key = outputs['ssh_private_key']['value']
        with tcp_tunnel(ip, 'oracle', private_key, 1521) as tunnel:
            ip, port = tunnel
            env_instance = {
                'server': '{}:{}'.format(ip, port),
                'user': 'datadog',
                'password': 'Oracle123',
                'service_name': 'orcl.c.datadog-integrations-lab.internal',
            }
            yield env_instance, E2E_METADATA


E2E_METADATA = {
    'start_commands': [
        'mkdir /opt/oracle',
        'apt-get update',
        'apt-get install libaio1 unzip',
        'curl -o /opt/oracle/instantclient.zip '
        'https://storage.googleapis.com/datadog-integrations-lab/instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip',
        'unzip /opt/oracle/instantclient.zip -d /opt/oracle',
    ],
    'env_vars': {'LD_LIBRARY_PATH': '/opt/oracle/instantclient_19_3'},
}
