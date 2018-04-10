# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import time

import pytest
import pymysql

import common


def wait_for_mysql():
    """
    Wait for the slave to connect to the master
    """
    connected = True
    for i in xrange(0, 100):
        try:
            db = pymysql.connect(
                host=common.HOST,
                port=common.PORT,
                user='root',
                connect_timeout=10
            )
            db = pymysql.connect(
                host=common.HOST,
                port=common.SLAVE_PORT,
                user='root',
                connect_timeout=10
            )
            connected = True
        except Exception as e:
            pass
            time.sleep(1)

    if not connected:
        raise Exception("It didn't work")


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
    env['MYSQL_PORT'] = common.PORT
    env['MYSQL_SLAVE_PORT'] = common.SLAVE_PORT

    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', _compose_file())
    ]

    subprocess.check_call(args + ["up", "-d"])
    # wait for the cluster to be up before yielding
    master = redis.Redis(port=MASTER_PORT, db=14, host=HOST)
    replica = redis.Redis(port=REPLICA_PORT, db=14, host=HOST)
    wait_for_mysql(master, replica):
    yield
    subprocess.check_call(args + ["down"])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def _compose_file():
    if _mysql_flavor() == 'mysql':
        return 'mysql.yaml'
    elif _mysql_flavor() == 'mariadb':
        return 'maria.yaml'

def _mysql_flavor():
    return os.getenv('MYSQL_FLAVOR', 'mysql')


def _mysql_version():
    return os.getenv('MYSQL_VERSION', 'mysql')


def _mysql_docker_repo():
    if _mysql_flavor() == 'mysql':
        if mysql_version() == '5.5':
            return 'jfullaondo/mysql-replication'
        else:
            return 'bergerx/mysql-replication'
        elif _mysql_flavor() == 'mariadb':
            return 'bitnami/mariadb'
