# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest
try:
    import pyodbc
except ImportError:
    pyodbc = None

from datadog_checks.dev import docker_run, WaitFor

from .common import (
    INIT_CONFIG, INIT_CONFIG_OBJECT_NAME, INSTANCE_SQL2008, INSTANCE_DOCKER, HOST, PORT, HERE, FULL_CONFIG, lib_tds_path
)


@pytest.fixture
def init_config():
    return deepcopy(INIT_CONFIG)


@pytest.fixture
def init_config_object_name():
    return deepcopy(INIT_CONFIG_OBJECT_NAME)


@pytest.fixture
def instance_sql2008():
    return deepcopy(INSTANCE_SQL2008)


@pytest.fixture
def instance_docker():
    return deepcopy(INSTANCE_DOCKER)


@pytest.fixture(scope='session')
def dd_environment():
    if pyodbc is None:
        raise Exception("pyodbc is not installed!")

    def sqlserver():
        conn = 'DRIVER={};Server={},{};Database=master;UID=sa;PWD=Password123;'.format(lib_tds_path(), HOST, PORT)
        pyodbc.connect(conn, timeout=30)

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[WaitFor(sqlserver, wait=3, attempts=10)]
    ):
        yield FULL_CONFIG
