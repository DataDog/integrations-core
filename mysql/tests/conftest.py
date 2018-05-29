# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import time
import os

import pytest
import pymysql
import logging

import common

log = logging.getLogger('test_mysql')


def wait_for_mysql():
    """
    Wait for the slave to connect to the master
    """
    connected = False
    for i in xrange(0, 100):
        try:
            pymysql.connect(
                host=common.HOST,
                port=common.PORT,
                user=common.USER,
                passwd=common.PASS,
                connect_timeout=2
            )
            pymysql.connect(
                host=common.HOST,
                port=common.SLAVE_PORT,
                user=common.USER,
                passwd=common.PASS,
                connect_timeout=2
            )
            connected = True
            return True
        except Exception as e:
            log.debug("exception: {}".format(e))
            time.sleep(2)

    return connected


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
    env['MYSQL_SHELL_SCRIPT'] = _mysql_shell_script()
    env['WAIT_FOR_IT_SCRIPT_PATH'] = _wait_for_it_script()
    env['MYSQL_SCRIPT_OPTIONS'] = _mysql_script_options()

    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', _compose_file())
    ]
    subprocess.check_call(args + ["down"], env=env)
    subprocess.check_call(args + ["up", "-d"], env=env)
    # wait for the cluster to be up before yielding
    if not wait_for_mysql():
        containers = [
            "compose_mysql-master_1",
            "compose_mysql-slave_1",
            "compose_mysql-setup_1",
        ]
        for container in containers:
            args = [
                "docker",
                "logs",
                container,
            ]
            subprocess.check_call(args, env=env)
        raise Exception("not working")
    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def _mysql_script_options():
    if _mysql_flavor() == 'mariadb':
        return '--password=master_root_password'
    return ''


def _compose_file():
    if _mysql_flavor() == 'mysql':
        return 'mysql.yaml'
    elif _mysql_flavor() == 'mariadb':
        return 'maria.yaml'


def _mysql_flavor():
    return os.getenv('MYSQL_FLAVOR', 'mysql')


def _mysql_version():
    return os.getenv('MYSQL_VERSION', 'mysql')


def _mysql_shell_script():
    return os.path.join(common.HERE, 'compose', 'setup_mysql.sh')


def _wait_for_it_script():
    dir = os.path.join(common.TESTS_HELPER_DIR, 'scripts', 'wait-for-it.sh')
    return os.path.abspath(dir)


def _mysql_docker_repo():
    if _mysql_flavor() == 'mysql':
        if _mysql_version() == '5.5':
            return 'jfullaondo/mysql-replication'
        else:
            return 'bergerx/mysql-replication'
    elif _mysql_flavor() == 'mariadb':
        return 'bitnami/mariadb'
