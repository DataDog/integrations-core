# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from .common import (
    DOCKER_SERVER,
    FULL_E2E_CONFIG,
    HERE,
    INIT_CONFIG,
    INIT_CONFIG_ALT_TABLES,
    INIT_CONFIG_OBJECT_NAME,
    INSTANCE_AO_DOCKER_SECONDARY,
    INSTANCE_DOCKER,
    INSTANCE_E2E,
    INSTANCE_SQL2017,
    INSTANCE_SQL2017_DEFAULTS,
    get_local_driver,
)

try:
    import pyodbc
except ImportError:
    pyodbc = None


@pytest.fixture
def init_config():
    return deepcopy(INIT_CONFIG)


@pytest.fixture
def init_config_object_name():
    return deepcopy(INIT_CONFIG_OBJECT_NAME)


@pytest.fixture
def init_config_alt_tables():
    return deepcopy(INIT_CONFIG_ALT_TABLES)


@pytest.fixture
def instance_sql2017_defaults():
    return deepcopy(INSTANCE_SQL2017_DEFAULTS)


@pytest.fixture
def instance_sql2017():
    return deepcopy(INSTANCE_SQL2017)


@pytest.fixture
def instance_docker():
    return deepcopy(INSTANCE_DOCKER)


@pytest.fixture
def instance_e2e():
    return deepcopy(INSTANCE_E2E)


@pytest.fixture
def instance_ao_docker_primary():
    instance = deepcopy(INSTANCE_DOCKER)
    instance['include_ao_metrics'] = True
    instance['driver'] = 'FreeTDS'
    return instance


@pytest.fixture
def instance_ao_docker_primary_local_only():
    instance = deepcopy(INSTANCE_DOCKER)
    instance['include_ao_metrics'] = True
    instance['driver'] = 'FreeTDS'
    instance['only_emit_local'] = True
    return instance


@pytest.fixture
def instance_ao_docker_primary_non_existing_ag():
    instance = deepcopy(INSTANCE_DOCKER)
    instance['include_ao_metrics'] = True
    instance['driver'] = 'FreeTDS'
    instance['availability_group'] = 'AG2'
    return instance


@pytest.fixture
def instance_ao_docker_secondary():
    return deepcopy(INSTANCE_AO_DOCKER_SECONDARY)


@pytest.fixture
def instance_autodiscovery():
    instance = deepcopy(INSTANCE_DOCKER)
    instance['database_autodiscovery'] = True
    return deepcopy(instance)


@pytest.fixture(scope='session')
def dd_environment():
    if pyodbc is None:
        raise Exception("pyodbc is not installed!")

    def sqlserver_can_connect():
        conn = 'DRIVER={};Server={};Database=master;UID=sa;PWD=Password123;'.format(get_local_driver(), DOCKER_SERVER)
        pyodbc.connect(conn, timeout=30)

    compose_file = os.path.join(HERE, os.environ["COMPOSE_FOLDER"], 'docker-compose.yaml')
    conditions = [
        WaitFor(sqlserver_can_connect, wait=3, attempts=10),
    ]

    if os.environ["COMPOSE_FOLDER"] == 'compose-ha':
        conditions += [
            CheckDockerLogs(
                compose_file,
                'Always On Availability Groups connection with primary database established for secondary database',
            )
        ]
    else:
        conditions += [
            CheckDockerLogs(
                compose_file,
                'setup.sql completed',
            )
        ]

    with docker_run(
        compose_file=compose_file,
        conditions=conditions,
        mount_logs=True,
    ):
        yield FULL_E2E_CONFIG
