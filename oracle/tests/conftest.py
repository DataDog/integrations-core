# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.oracle import Oracle

from .common import (
    CHECK_NAME,
    CLIENT_LIB,
    COMPOSE_FILE,
    CONTAINER_NAME,
    HOST,
    ORACLE_DATABASE_VERSION,
    PASSWORD,
    PORT,
    USER,
)

INSTANT_CLIENT_URL = (
    "https://ddintegrations.blob.core.windows.net/oracle/instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip"
)

E2E_METADATA_ORACLE_CLIENT = {
    'start_commands': [
        'mkdir /opt/oracle',
        'apt-get update',
        'apt-get install libaio1 unzip',
        'curl -o /opt/oracle/instantclient.zip {}'.format(INSTANT_CLIENT_URL),
        'unzip /opt/oracle/instantclient.zip -d /opt/oracle',
    ],
    'env_vars': {'LD_LIBRARY_PATH': '/opt/oracle/instantclient_19_3'},
}

E2E_METADATA_JDBC_CLIENT = {
    # Since we don't include Oracle instantclient to `LD_LIBRARY_PATH` env var,
    # the integration will fallback to JDBC client
    'use_jmx': True,  # Using jmx to have a ready to use java runtime
    'start_commands': [
        'mkdir /opt/oracle',
        'apt-get update',
        'apt-get install unzip',
        # JDBC client needs Oracle driver `ojdbc8.jar` from Instant Client
        'curl -o /opt/oracle/instantclient.zip {}'.format(INSTANT_CLIENT_URL),
        'unzip /opt/oracle/instantclient.zip -d /opt/oracle',
    ],
}


@pytest.fixture
def check(instance):
    return Oracle(CHECK_NAME, {}, [instance])


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
    instance = {
        'server': '{}:{}'.format(HOST, PORT),
        'user': USER,
        'password': PASSWORD,
        'service_name': 'InfraDB.us.oracle.com',
    }

    if CLIENT_LIB == 'jdbc':
        e2e_metadata = E2E_METADATA_JDBC_CLIENT
        instance['jdbc_driver_path'] = '/opt/oracle/instantclient_19_3/ojdbc8.jar'
    else:
        e2e_metadata = E2E_METADATA_ORACLE_CLIENT

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
