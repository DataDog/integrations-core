# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.ssh_tunnel import tcp_tunnel
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.dev.utils import get_here
from datadog_checks.oracle import Oracle

from .common import (
    CLIENT_LIB,
    COMPOSE_FILE,
    CONTAINER_NAME,
    ENV_TYPE,
    HOST,
    ORACLE_DATABASE_VERSION,
    PASSWORD,
    PORT,
    USER,
)

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
    instance = {}
    if CLIENT_LIB == 'jdbc':
        e2e_metadata = E2E_METADATA_JDBC_CLIENT
        instance['jdbc_driver_path'] = '/opt/oracle/instantclient_19_3/ojdbc8.jar'
    else:
        e2e_metadata = E2E_METADATA_ORACLE_CLIENT

    if ENV_TYPE == 'terraform':
        with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
            ip = outputs['ip']['value']
            private_key = outputs['ssh_private_key']['value']
            with tcp_tunnel(ip, 'oracle', private_key, 1521) as tunnel:
                ip, port = tunnel
                instance.update(
                    {
                        'server': '{}:{}'.format(ip, port),
                        'user': USER,
                        'password': PASSWORD,
                        'service_name': 'orcl.c.datadog-integrations-lab.internal',
                    }
                )
                yield instance, e2e_metadata
    else:
        instance.update(
            {
                'server': '{}:{}'.format(HOST, PORT),
                'user': USER,
                'password': PASSWORD,
                'service_name': 'InfraDB.us.oracle.com',
            }
        )
        with docker_run(
            COMPOSE_FILE,
            conditions=[
                CheckDockerLogs(COMPOSE_FILE, ['The database is ready for use'], wait=5, attempts=120),
                WaitFor(create_user),
            ],
            env_vars={'ORACLE_DATABASE_VERSION': ORACLE_DATABASE_VERSION},
        ):
            yield instance, e2e_metadata


def create_user():
    output = run_docker_command(
        [
            '/u01/app/oracle/product/12.2.0/dbhome_1/bin/sqlplus',
            'sys/Oradoc_db1@localhost:1521/InfraDB.us.oracle.com',
            'AS',
            'SYSDBA',
            '@/host/data/setup.sql',
        ]
    )

    return 'Grant succeeded.' in output.stdout


def run_docker_command(command):
    cmd = ['docker', 'exec', CONTAINER_NAME] + command
    return run_command(cmd, capture=True, check=True)


E2E_METADATA_ORACLE_CLIENT = {
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

E2E_METADATA_JDBC_CLIENT = {
    'use_jmx': True,  # Using jmx to have a ready to use java runtime
    'start_commands': [
        'mkdir /opt/oracle',
        'apt-get update',
        'apt-get install libaio1 unzip',
        'curl -o /opt/oracle/instantclient.zip '
        'https://storage.googleapis.com/datadog-integrations-lab/instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip',
        'unzip /opt/oracle/instantclient.zip -d /opt/oracle',
    ],
}
