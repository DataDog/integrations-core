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
    HERE,
    HOST,
    INIT_CONFIG,
    INIT_CONFIG_ALT_TABLES,
    INIT_CONFIG_OBJECT_NAME,
    get_local_driver,
)
from .utils import HighCardinalityQueries

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


@pytest.fixture(scope="session")
def instance_session_default():
    instance = {
        'host': '{},1433'.format(HOST),
        'connector': 'odbc',
        'driver': get_local_driver(),
        'username': 'datadog',
        'password': 'Password12!',
        'disable_generic_tags': True,
        'tags': ['optional:tag1'],
    }
    windows_sqlserver_driver = os.environ.get('WINDOWS_SQLSERVER_DRIVER', None)
    if not windows_sqlserver_driver or windows_sqlserver_driver == 'odbc':
        instance['connection_string'] = 'TrustServerCertificate=yes'
        return instance
    instance['adoprovider'] = windows_sqlserver_driver
    instance['connector'] = 'adodbapi'
    return instance


@pytest.fixture
def instance_docker_defaults(instance_session_default):
    # deepcopy necessary here because we want to make sure each test invocation gets its own unique copy of the instance
    # this also means that none of the test need to defensively make their own copies
    return deepcopy(instance_session_default)


@pytest.fixture
def instance_docker_metrics(instance_session_default):
    '''
    This fixture is used to test the metrics that are emitted from the integration main check.
    We disable all DBM checks and only care about the main check metrics.
    '''
    instance = deepcopy(instance_session_default)
    instance['dbm'] = False
    return instance


@pytest.fixture
def instance_minimal_defaults():
    return {
        'host': DOCKER_SERVER,
        'username': 'sa',
        'password': 'Password12!',
        'disable_generic_tags': True,
    }


@pytest.fixture
def instance_docker(instance_docker_defaults):
    instance_docker_defaults.update(
        {
            'include_task_scheduler_metrics': True,
            'include_db_fragmentation_metrics': True,
            'include_fci_metrics': True,
            'include_ao_metrics': False,
            'include_master_files_metrics': True,
            'disable_generic_tags': True,
        }
    )
    return instance_docker_defaults


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
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
        instance_docker['driver'], instance_docker['host'], instance_docker['username'], instance_docker['password']
    )
    conn = _common_pyodbc_connect(conn_str)
    yield conn
    conn.close()


@pytest.fixture
def bob_conn_str(instance_docker):
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
        instance_docker['driver'], instance_docker['host'], "bob", "Password12!"
    )
    return conn_str


@pytest.fixture
def bob_conn(bob_conn_str):
    # Make DB connection
    conn = SelfHealingConnection(bob_conn_str)
    conn.reconnect()
    yield conn
    conn.close()


@pytest.fixture
def bob_conn_raw(bob_conn_str):
    # Make DB connection
    conn = _common_pyodbc_connect(bob_conn_str)
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
                    return
            except Exception:
                tracebacks.append(",".join(traceback.format_exception(*sys.exc_info())))
                logging.exception("failed to execute query attempt=%s", attempt)
                time.sleep(sleep)
                self.reconnect()

        raise Exception("failed to execute query after {} retries:\n {}".format(retries, "\n".join(tracebacks)))


@pytest.fixture
def sa_conn(instance_docker):
    # system administrator connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
        instance_docker['driver'], instance_docker['host'], "sa", "Password123"
    )
    conn = _common_pyodbc_connect(conn_str)
    yield conn
    conn.close()


@pytest.fixture
def instance_e2e(instance_docker):
    instance_docker['driver'] = '{ODBC Driver 18 for SQL Server}'
    instance_docker['dbm'] = True
    return instance_docker


@pytest.fixture
def instance_ao_docker_primary(instance_docker):
    instance_docker['include_ao_metrics'] = True
    return instance_docker


@pytest.fixture
def instance_ao_docker_primary_local_only(instance_ao_docker_primary):
    instance = deepcopy(instance_ao_docker_primary)
    instance['only_emit_local'] = True
    return instance


@pytest.fixture
def instance_ao_docker_primary_non_existing_ag(instance_ao_docker_primary):
    instance = deepcopy(instance_ao_docker_primary)
    instance['availability_group'] = 'AG2'
    return instance


@pytest.fixture
def instance_ao_docker_secondary(instance_ao_docker_primary):
    instance = deepcopy(instance_ao_docker_primary)
    instance['host'] = '{},1434'.format(HOST)
    return instance


@pytest.fixture
def instance_autodiscovery(instance_docker):
    instance_docker['database_autodiscovery'] = True
    return instance_docker


def pytest_addoption(parser):
    parser.addoption(
        "--run_high_cardinality_forever",
        action="store_true",
        default=False,
        help="run a test that executes high cardinality queries forever unless it's terminated",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "run_high_cardinality_forever: mark a test to run high cardinality queries forever"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run_high_cardinality_forever"):
        # --run_high_cardinality_forever given in cli: do not skip test
        return
    skip_run_high_cardinality_forever = pytest.mark.skip(reason="need --run_high_cardinality_forever option to run")
    for item in items:
        if "run_high_cardinality_forever" in item.keywords:
            item.add_marker(skip_run_high_cardinality_forever)


E2E_METADATA = {'docker_platform': 'windows' if using_windows_containers() else 'linux'}


@pytest.fixture(scope='session')
def full_e2e_config(instance_session_default):
    return {"init_config": INIT_CONFIG, "instances": [instance_session_default]}


@pytest.fixture(scope='session')
def dd_environment(full_e2e_config):
    if pyodbc is None:
        raise Exception("pyodbc is not installed!")

    def sqlserver_can_connect():
        conn_str = 'DRIVER={};Server={};Database=master;UID=sa;PWD=Password123;TrustServerCertificate=yes;'.format(
            get_local_driver(), DOCKER_SERVER
        )
        pyodbc.connect(conn_str, timeout=DEFAULT_TIMEOUT, autocommit=True)

    def high_cardinality_env_is_ready():
        return HighCardinalityQueries(
            {'driver': get_local_driver(), 'host': DOCKER_SERVER, 'username': 'sa', 'password': 'Password123'}
        ).is_ready()

    compose_file = os.path.join(HERE, os.environ["COMPOSE_FOLDER"], 'docker-compose.yaml')
    conditions = [WaitFor(sqlserver_can_connect, wait=3, attempts=10)]

    completion_message = 'INFO: setup.sql completed.'
    if os.environ["COMPOSE_FOLDER"] == 'compose-ha':
        completion_message = (
            'Always On Availability Groups connection with primary database established ' 'for secondary database'
        )
    if 'compose-high-cardinality' in os.environ["COMPOSE_FOLDER"]:
        # This env is a highly loaded database and is expected to take a while to setup.
        # This will wait about 8 minutes before timing out.
        conditions += [WaitFor(high_cardinality_env_is_ready, wait=5, attempts=90)]

    conditions += [CheckDockerLogs(compose_file, completion_message)]

    with docker_run(compose_file=compose_file, conditions=conditions, mount_logs=True, build=True, attempts=3):
        yield full_e2e_config, E2E_METADATA
