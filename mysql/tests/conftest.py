# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pymysql
import pytest

from datadog_checks.dev import WaitFor, docker_run
from . import common, tags


MYSQL_FLAVOR = os.getenv('MYSQL_FLAVOR', 'mysql')
COMPOSE_FILE = '{}.yaml'.format(MYSQL_FLAVOR)


@pytest.fixture(scope='session')
def dd_environment(instance_basic):
    with docker_run(
        os.path.join(common.HERE, 'compose', COMPOSE_FILE),
        env_vars={
            'MYSQL_DOCKER_REPO': _mysql_docker_repo(),
            'MYSQL_PORT': str(common.PORT),
            'MYSQL_SLAVE_PORT': str(common.SLAVE_PORT),
            'WAIT_FOR_IT_SCRIPT_PATH': _wait_for_it_script(),
        },
        conditions=[
            WaitFor(connect_master, wait=2),
            WaitFor(connect_slave, wait=2),
        ],
    ):
        yield instance_basic


@pytest.fixture(scope='session')
def instance_basic():
    return {
        'server': common.HOST,
        'user': common.USER,
        'pass': common.PASS,
        'port': common.PORT,
    }


@pytest.fixture
def instance_complex():
    return {
        'server': common.HOST,
        'user': common.USER,
        'pass': common.PASS,
        'port': common.PORT,
        'options': {
            'replication': True,
            'extra_status_metrics': True,
            'extra_innodb_metrics': True,
            'extra_performance_metrics': True,
            'schema_size_metrics': True,
        },
        'tags': tags.METRIC_TAGS,
        'queries': [
            {
                'query': "SELECT * from testdb.users where name='Alice' limit 1;",
                'metric': 'alice.age',
                'type': 'gauge',
                'field': 'age'
            },
            {
                'query': "SELECT * from testdb.users where name='Bob' limit 1;",
                'metric': 'bob.age',
                'type': 'gauge',
                'field': 'age'
            },
        ],
    }


@pytest.fixture(scope='session')
def instance_error():
    return {
        'server': common.HOST,
        'user': 'unknown',
        'pass': common.PASS,
    }


def connect_master():
    passw = common.MARIA_ROOT_PASS if MYSQL_FLAVOR == 'mariadb' else ''
    conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root', password=passw)
    _setup_master(conn)


def connect_slave():
    pymysql.connect(host=common.HOST, port=common.SLAVE_PORT, user=common.USER, passwd=common.PASS)


def _setup_master(conn):
    cur = conn.cursor()
    cur.execute("CREATE USER 'dog'@'%' IDENTIFIED BY 'dog';")
    cur.execute("GRANT REPLICATION CLIENT ON *.* TO 'dog'@'%' WITH MAX_USER_CONNECTIONS 5;")
    cur.execute("GRANT PROCESS ON *.* TO 'dog'@'%';")
    cur.execute("CREATE DATABASE testdb;")
    cur.execute("CREATE TABLE testdb.users (name VARCHAR(20), age INT);")
    cur.execute("GRANT SELECT ON testdb.users TO 'dog'@'%'")
    cur.execute("INSERT INTO testdb.users (name,age) VALUES('Alice',25);")
    cur.execute("INSERT INTO testdb.users (name,age) VALUES('Bob',20);")
    cur.execute("GRANT SELECT ON performance_schema.* TO 'dog'@'%'")
    cur.close()


def _wait_for_it_script():
    """
    FIXME: relying on the filesystem layout is a bad idea, the testing helper
    should expose its path through the api instead
    """
    script = os.path.join(common.TESTS_HELPER_DIR, 'scripts', 'wait-for-it.sh')
    return os.path.abspath(script)


def _mysql_docker_repo():
    if MYSQL_FLAVOR == 'mysql':
        if os.getenv('MYSQL_VERSION') == '5.5':
            return 'jfullaondo/mysql-replication'
        else:
            return 'bergerx/mysql-replication'
    elif MYSQL_FLAVOR == 'mariadb':
        return 'bitnami/mariadb'
