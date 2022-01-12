# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import sys
import time
import traceback
from copy import deepcopy

import pytest

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.docker import using_windows_containers

from .common import (
    DOCKER_SERVER,
    FULL_E2E_CONFIG,
    HERE,
    INIT_CONFIG,
    INIT_CONFIG_ALT_TABLES,
    INIT_CONFIG_OBJECT_NAME,
    INSTANCE_AO_DOCKER_SECONDARY,
    INSTANCE_DOCKER,
    INSTANCE_DOCKER_DEFAULTS,
    INSTANCE_E2E,
    INSTANCE_SQL,
    INSTANCE_SQL_DEFAULTS,
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
def instance_sql_defaults():
    return deepcopy(INSTANCE_SQL_DEFAULTS)


@pytest.fixture
def instance_sql_msoledb():
    instance = deepcopy(INSTANCE_SQL_DEFAULTS)
    instance['adoprovider'] = "MSOLEDBSQL"
    return instance


@pytest.fixture
def instance_sql():
    return deepcopy(INSTANCE_SQL)


@pytest.fixture
def instance_docker():
    return deepcopy(INSTANCE_DOCKER)


@pytest.fixture
def instance_docker_defaults():
    return deepcopy(INSTANCE_DOCKER_DEFAULTS)


# the default timeout in the integration tests is deliberately elevated beyond the default timeout in the integration
# itself in order to reduce flakiness due to any sort of slowness in the tests
DEFAULT_TIMEOUT = 30


def _common_pyodbc_connect(conn_str):
    # all connections must have the correct timeouts set
    # if the statement timeout is not set then the integration tests can *hang* for a very long time if, for example,
    # a query is blocked on something.
    conn = pyodbc.connect(conn_str, timeout=DEFAULT_TIMEOUT, autocommit=True)
    conn.timeout = DEFAULT_TIMEOUT

    def _sanity_check_query():
        with conn.cursor() as cursor:
            cursor.execute("select 1")
            cursor.fetchall()

    WaitFor(_sanity_check_query, wait=3, attempts=10)()

    return conn


@pytest.fixture
def datadog_conn_docker(instance_docker):
    # Make DB connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
        instance_docker['driver'], instance_docker['host'], instance_docker['username'], instance_docker['password']
    )
    conn = _common_pyodbc_connect(conn_str)
    yield conn
    conn.close()


@pytest.fixture
def bob_conn(instance_docker):
    # Make DB connection

    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
        instance_docker['driver'], instance_docker['host'], "bob", "Password12!"
    )
    conn = SelfHealingConnection(conn_str)
    conn.reconnect()
    yield conn
    conn.close()


class SelfHealingConnection:
    """
    A connection that is able to retry queries after completely reinitializing the database connection.
    Sometimes connections enter a bad state during tests which can cause cursors to fail or time out inexplicably.
    By using this self-healing connection we enable tests to automatically recover and reduce flakiness.
    """

    def __init__(self, conn_str):
        self.conn_str = conn_str
        self.conn = None
        self.reconnect()

    def reconnect(self):
        self.close()
        self.conn = _common_pyodbc_connect(self.conn_str)

    def close(self):
        try:
            if self.conn:
                logging.info("recreating connection")
                self.conn.close()
        except Exception:
            logging.exception("failed to close connection")

    def execute_with_retries(self, query, params=(), database=None, retries=3, sleep=1, return_result=True):
        tracebacks = []
        for attempt in range(retries):
            try:
                logging.info("executing query with retries. query='%s' params=%s attempt=%s", query, params, attempt)
                with self.conn.cursor() as cursor:
                    if database:
                        cursor.execute("USE {}".format(database))
                    cursor.execute(query, params)
                    if return_result:
                        return cursor.fetchall()
            except Exception:
                tracebacks.append(",".join(traceback.format_exception(*sys.exc_info())))
                logging.exception("failed to execute query attempt=%s", attempt)
                time.sleep(sleep)
                self.reconnect()

        raise Exception("failed to execute query after {} retries:\n {}".format(retries, "\n".join(tracebacks)))


@pytest.fixture
def sa_conn(instance_docker):
    # system administrator connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
        instance_docker['driver'], instance_docker['host'], "sa", "Password123"
    )
    conn = _common_pyodbc_connect(conn_str)
    yield conn
    conn.close()


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


E2E_METADATA = {'docker_platform': 'windows' if using_windows_containers() else 'linux'}


@pytest.fixture(scope='session')
def dd_environment():
    if pyodbc is None:
        raise Exception("pyodbc is not installed!")

    def sqlserver_can_connect():
        conn = 'DRIVER={};Server={};Database=master;UID=sa;PWD=Password123;'.format(get_local_driver(), DOCKER_SERVER)
        pyodbc.connect(conn, timeout=DEFAULT_TIMEOUT, autocommit=True)

    compose_file = os.path.join(HERE, os.environ["COMPOSE_FOLDER"], 'docker-compose.yaml')
    conditions = [
        WaitFor(sqlserver_can_connect, wait=3, attempts=10),
    ]

    completion_message = 'sqlserver setup completed'
    if os.environ["COMPOSE_FOLDER"] == 'compose-ha':
        completion_message = (
            'Always On Availability Groups connection with primary database established ' 'for secondary database'
        )

    conditions += [CheckDockerLogs(compose_file, completion_message)]

    with docker_run(compose_file=compose_file, conditions=conditions, mount_logs=True, build=True, attempts=2):
        yield FULL_E2E_CONFIG, E2E_METADATA
