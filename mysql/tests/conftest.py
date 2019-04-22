# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pymysql
import pytest

from datadog_checks.dev import WaitFor, docker_run

from . import common, tags

MYSQL_FLAVOR = os.getenv('MYSQL_FLAVOR')
MYSQL_VERSION = os.getenv('MYSQL_VERSION')
COMPOSE_FILE = os.getenv('COMPOSE_FILE')


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
        conditions=[WaitFor(init_master, wait=2), WaitFor(init_slave, wait=2)],
    ):
        master_conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root')
        _populate_database(master_conn)
        yield instance_basic


@pytest.fixture(scope='session')
def instance_basic():
    return {'server': common.HOST, 'user': common.USER, 'pass': common.PASS, 'port': common.PORT}


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
                'field': 'age',
            },
            {
                'query': "SELECT * from testdb.users where name='Bob' limit 1;",
                'metric': 'bob.age',
                'type': 'gauge',
                'field': 'age',
            },
        ],
    }


@pytest.fixture(scope='session')
def instance_error():
    return {'server': common.HOST, 'user': 'unknown', 'pass': common.PASS}


def init_master():
    conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root')
    _add_dog_user(conn)


def init_slave():
    pymysql.connect(host=common.HOST, port=common.SLAVE_PORT, user=common.USER, passwd=common.PASS)


def _add_dog_user(conn):
    cur = conn.cursor()
    cur.execute("CREATE USER 'dog'@'%' IDENTIFIED BY 'dog';")
    if MYSQL_FLAVOR == 'mysql' and MYSQL_VERSION == '8.0':
        cur.execute("GRANT REPLICATION CLIENT ON *.* TO 'dog'@'%';")
        cur.execute("ALTER USER 'dog'@'%' WITH MAX_USER_CONNECTIONS 5;")
    else:
        cur.execute("GRANT REPLICATION CLIENT ON *.* TO 'dog'@'%' WITH MAX_USER_CONNECTIONS 5;")
    cur.execute("GRANT PROCESS ON *.* TO 'dog'@'%';")
    cur.execute("GRANT SELECT ON performance_schema.* TO 'dog'@'%'")


def _populate_database(conn):
    cur = conn.cursor()
    cur.execute("USE mysql;")
    cur.execute("CREATE DATABASE testdb;")
    cur.execute("USE testdb;")
    cur.execute("CREATE TABLE testdb.users (name VARCHAR(20), age INT);")
    cur.execute("INSERT INTO testdb.users (name,age) VALUES('Alice',25);")
    cur.execute("INSERT INTO testdb.users (name,age) VALUES('Bob',20);")
    cur.execute("GRANT SELECT ON testdb.users TO 'dog'@'%';")
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
        if MYSQL_VERSION == '5.5':
            return 'jfullaondo/mysql-replication'
        elif MYSQL_VERSION in ('5.6', '5.7'):
            return 'bergerx/mysql-replication'
        elif MYSQL_VERSION == '8.0':
            return 'bitnami/mysql'
    elif MYSQL_FLAVOR == 'mariadb':
        return 'bitnami/mariadb'
