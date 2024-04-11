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
    ENABLE_TCPS,
    HERE,
    HOST,
    ORACLE_DATABASE_VERSION,
    PASSWORD,
    PORT,
    TCPS_PORT,
    USER,
)

E2E_METADATA_JDBC_CLIENT = {
    # The integration will use to JDBC client
    'use_jmx': True,  # Using jmx to have a ready to use java runtime
    'docker_volumes': [
        '{}/scripts/install_jdbc_client.sh:/tmp/install_jdbc_client.sh'.format(HERE),
        '{}/docker/client/client_wallet:/opt/oracle/instantclient_19_3/client_wallet'.format(HERE),
        '{}/docker/client/sqlnet.ora:/opt/oracle/instantclient_19_3/sqlnet.ora'.format(HERE),
        '{}/docker/client/tnsnames.ora:/opt/oracle/instantclient_19_3/tnsnames.ora'.format(HERE),
        '{}/docker/client/listener.ora:/opt/oracle/instantclient_19_3/listener.ora'.format(HERE),
        '{}/docker/client/oraclepki.jar:/opt/oracle/instantclient_19_3/oraclepki.jar'.format(HERE),
        '{}/docker/client/osdt_cert.jar:/opt/oracle/instantclient_19_3/osdt_cert.jar'.format(HERE),
        '{}/docker/client/osdt_core.jar:/opt/oracle/instantclient_19_3/osdt_core.jar'.format(HERE),
    ],
    'start_commands': [
        'bash /tmp/install_jdbc_client.sh',  # Still needed to set up the database
    ],
    'env_vars': {'TNS_ADMIN': '/opt/oracle/instantclient_19_3'},
}

E2E_METADATA_ORACLE_CLIENT = {
    'use_jmx': True,  # update-ca-certificates fails without this
    'docker_volumes': [
        '{}/scripts/install_jdbc_client.sh:/tmp/install_jdbc_client.sh'.format(HERE),
        '{}/docker/client/client_wallet:/opt/oracle/instantclient_19_3/client_wallet'.format(HERE),
        '{}/docker/client/sqlnet.ora:/opt/oracle/instantclient_19_3/sqlnet.ora'.format(HERE),
        '{}/docker/client/tnsnames.ora:/opt/oracle/instantclient_19_3/tnsnames.ora'.format(HERE),
        '{}/docker/client/listener.ora:/opt/oracle/instantclient_19_3/listener.ora'.format(HERE),
        '{}/docker/client/sqlnet.ora:/opt/oracle/instantclient_19_3/network/admin/sqlnet.ora'.format(HERE),
        '{}/docker/client/tnsnames.ora:/opt/oracle/instantclient_19_3/network/admin/tnsnames.ora'.format(HERE),
        '{}/docker/client/client_wallet/cwallet.sso:/opt/oracle/instantclient_19_3/network/admin/cwallet.sso'.format(
            HERE
        ),
    ],
    'start_commands': [
        'bash /tmp/install_jdbc_client.sh',
        'mkdir -p /usr/local/share/ca-certificates',
        'cp /opt/oracle/instantclient_19_3/client_wallet/cert.pem /usr/local/share/ca-certificates/ca-certificate.crt',
        'update-ca-certificates --verbose --fresh',
    ],
    'env_vars': {
        'LD_LIBRARY_PATH': '/opt/oracle/instantclient_19_3',
    },
}


@pytest.fixture
def check(instance):
    return Oracle(CHECK_NAME, {"use_instant_client": False}, [instance])


@pytest.fixture
def tcps_check(tcps_instance):
    return Oracle(CHECK_NAME, {"use_instant_client": False}, [tcps_instance])


@pytest.fixture
def instance():
    return {
        'server': 'localhost:1521',
        'username': 'system',
        'password': 'oracle',
        'service_name': 'xe',
        'protocol': 'TCP',
        'tags': ['optional:tag1'],
        'loader': 'python',
    }


@pytest.fixture
def tcps_instance():
    return {
        'server': 'localhost:2484',
        'username': 'system',
        'password': 'oracle',
        'service_name': 'xe',
        'protocol': 'TCP',
        'tags': ['optional:tag1'],
        'loader': 'python',
    }


@pytest.fixture(scope='session')
def dd_environment():
    instance = {
        'server': '{}:{}'.format(HOST, PORT),
        'username': USER,
        'password': PASSWORD,
        'service_name': 'InfraDB.us.oracle.com',
        'protocol': 'TCP',
        'loader': 'python',
    }

    use_instant_client = False

    if CLIENT_LIB == 'jdbc':
        e2e_metadata = E2E_METADATA_JDBC_CLIENT
        instance['jdbc_driver_path'] = '/opt/oracle/instantclient_19_3/ojdbc8.jar'
    else:
        e2e_metadata = E2E_METADATA_ORACLE_CLIENT
        if CLIENT_LIB == 'oracle-instant-client':
            use_instant_client = True

    # Set additional config options for TCPS
    if ENABLE_TCPS:
        instance['server'] = '{}:{}'.format(HOST, TCPS_PORT)
        instance['protocol'] = 'TCPS'

        if CLIENT_LIB == 'jdbc':
            instance['jdbc_truststore_path'] = '/opt/oracle/instantclient_19_3/client_wallet/cwallet.sso'
            instance['jdbc_truststore_type'] = 'SSO'

    with docker_run(
        COMPOSE_FILE,
        conditions=[
            CheckDockerLogs(COMPOSE_FILE, ['The database is ready for use'], wait=5, attempts=120),
            WaitFor(create_user),
        ],
        env_vars={'ORACLE_DATABASE_VERSION': ORACLE_DATABASE_VERSION},
        attempts=20,
        attempts_wait=5,
        build=True,
    ):
        yield {
            'init_config': {"use_instant_client": use_instant_client},
            'instances': [instance],
        }, e2e_metadata


@pytest.fixture
def bad_instance():
    return {
        "password": "badpassword",
        "protocol": "TCP",
        "server": "localhost:1521",
        "service_name": "InfraDB.us.oracle.com",
        "username": "datadog",
        "loader": "python",
    }


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
