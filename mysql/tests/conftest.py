# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import time
import os
import sys

import pytest
import pymysql

from . import common


MYSQL_FLAVOR = os.getenv('MYSQL_FLAVOR', 'mysql')
COMPOSE_FILE = '{}.yaml'.format(MYSQL_FLAVOR)


@pytest.fixture(scope="session")
def spin_up_mysql():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    env = os.environ
    env['MYSQL_DOCKER_REPO'] = _mysql_docker_repo()
    env['MYSQL_PORT'] = str(common.PORT)
    env['MYSQL_SLAVE_PORT'] = str(common.SLAVE_PORT)
    env['WAIT_FOR_IT_SCRIPT_PATH'] = _wait_for_it_script()

    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', COMPOSE_FILE)
    ]

    subprocess.check_call(args + ["up", "-d"], env=env)

    # wait for the master and setup the database
    started = False
    for _ in xrange(15):
        try:
            passw = common.MARIA_ROOT_PASS if MYSQL_FLAVOR == 'mariadb' else ''
            conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root', password=passw)
            _setup_master(conn)
            sys.stderr.write("Master connected!\n")
            started = True
            break
        except Exception as e:
            sys.stderr.write("Exception starting master: {}\n".format(e))
            time.sleep(2)

    if not started:
        subprocess.check_call(args + ["logs", "mysql-master"], env=env)
        subprocess.check_call(args + ["down"], env=env)
        raise Exception("Timeout starting master")

    # wait for the slave
    started = False
    for _ in xrange(60):
        try:
            pymysql.connect(host=common.HOST, port=common.SLAVE_PORT, user=common.USER, passwd=common.PASS)
            sys.stderr.write("Slave connected!\n")
            started = True
            break
        except Exception as e:
            sys.stderr.write("Exception starting slave: {}\n".format(e))
            time.sleep(2)

    if not started:
        subprocess.check_call(args + ["logs", "mysql-slave"], env=env)
        subprocess.check_call(args + ["down"], env=env)
        raise Exception("Timeout starting slave")

    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


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
    dir = os.path.join(common.TESTS_HELPER_DIR, 'scripts', 'wait-for-it.sh')
    return os.path.abspath(dir)


def _mysql_docker_repo():
    if MYSQL_FLAVOR == 'mysql':
        if os.getenv('MYSQL_VERSION') == '5.5':
            return 'jfullaondo/mysql-replication'
        else:
            return 'bergerx/mysql-replication'
    elif MYSQL_FLAVOR == 'mariadb':
        return 'bitnami/mariadb'
