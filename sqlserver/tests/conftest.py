# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
import sys

import pytest
try:
    import pyodbc
except ImportError:
    pyodbc = None

from datadog_checks.dev import docker_run, get_docker_hostname, RetryError


HOST = get_docker_hostname()
PORT = 1433
HERE = os.path.dirname(os.path.abspath(__file__))


def lib_tds_path():
    """
    This is definitely ugly but should do the trick most of the times. On OSX
    we can point unixODBC directly to the FreeTDS client library. On linux instead
    we need to define the 'FreeTDS' driver in odbcinst.ini
    """
    if sys.platform == 'darwin':
        return '/usr/local/lib/libtdsodbc.so'
    return 'FreeTDS'


@pytest.fixture
def init_config():
    return {
        'custom_metrics': [
            {
                'name': 'sqlserver.clr.execution',
                'type': 'gauge',
                'counter_name': 'CLR Execution',
            },
            {
                'name': 'sqlserver.exec.in_progress',
                'type': 'gauge',
                'counter_name': 'OLEDB calls',
                'instance_name': 'Cumulative execution time (ms) per second',
            },
            {
                'name': 'sqlserver.db.commit_table_entries',
                'type': 'gauge',
                'counter_name': 'Log Flushes/sec',
                'instance_name': 'ALL',
                'tag_by': 'db',
            },
        ],
    }


@pytest.fixture
def instance_sql2008():
    return {
        'host': '(local)\SQL2008R2SP2',
        'username': 'sa',
        'password': 'Password12!',
    }


@pytest.fixture
def instance_docker():
    return {
        'host': '{},1433'.format(HOST),
        'connector': 'odbc',
        'driver': lib_tds_path(),
        'username': 'sa',
        'password': 'Password123',
        'tags': ['optional:tag1'],
    }


@pytest.fixture(scope='session')
def sqlserver():
    if pyodbc is None:
        raise Exception("pyodbc is not installed!")

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    conn = 'DRIVER={};Server={},{};Database=master;UID=sa;PWD=Password123;'
    conn = conn.format(lib_tds_path(), HOST, PORT)

    def condition():
        sys.stderr.write("Waiting for SQLServer to boot...\n")
        booted = False
        for _ in xrange(10):
            try:
                pyodbc.connect(conn, timeout=30)
                booted = True
            except pyodbc.Error as e:
                sys.stderr.write(str(e)+'\n')
                time.sleep(3)

        if not booted:
            raise RetryError("SQLServer failed to boot!")
        sys.stderr.write("SQLServer boot complete.\n")

    with docker_run(compose_file=compose_file, conditions=[condition]):
        yield
