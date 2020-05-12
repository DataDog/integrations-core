# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import WaitFor, docker_run

from .common import (
    DOCKER_SERVER,
    E2E_METADATA,
    FULL_CONFIG,
    HERE,
    INIT_CONFIG,
    INIT_CONFIG_OBJECT_NAME,
    INSTANCE_DOCKER,
    INSTANCE_SQL2017,
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
def instance_sql2017():
    return deepcopy(INSTANCE_SQL2017)


@pytest.fixture
def instance_docker():
    return deepcopy(INSTANCE_DOCKER)


@pytest.fixture(scope='session')
def dd_environment():
    if pyodbc is None:
        raise Exception("pyodbc is not installed!")

    def sqlserver():
        conn = 'DRIVER={};Server={};Database=master;UID=sa;PWD=Password123;'.format(get_local_driver(), DOCKER_SERVER)
        pyodbc.connect(conn, timeout=30)

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[WaitFor(sqlserver, wait=3, attempts=10)],
        mount_logs=True,
    ):
        yield FULL_CONFIG, E2E_METADATA
