import os
from copy import deepcopy

import pymysql
import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

DOCKER_HOST = get_docker_hostname()
MYSQL_PORT = 6612
PROXY_PORT = 6033
PROXY_ADMIN_PORT = 6032
MYSQL_USER = 'proxysql'
MYSQL_PASS = 'pass'
PROXY_ADMIN_USER = 'proxy'
PROXY_ADMIN_PASS = 'proxy'
MYSQL_DATABASE = 'test'

BASIC_INSTANCE = {
    'host': DOCKER_HOST,
    'port': PROXY_ADMIN_PORT,
    'username': PROXY_ADMIN_USER,
    'password': PROXY_ADMIN_PASS,
    'tags': ["application:test"],
    'additional_metrics': [],
}


@pytest.fixture
def instance_basic():
    return deepcopy(BASIC_INSTANCE)


@pytest.fixture()
def instance_all_metrics(instance_basic):
    instance_basic['additional_metrics'] = [
        'command_counters_metrics',
        'connection_pool_metrics',
        'users_metrics',
        'memory_metrics',
        'query_rules_metrics',
    ]
    return instance_basic


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'compose/docker-compose.yml')

    with docker_run(
        compose_file,
        env_vars={
            'PROXY_ADMIN_PORT': str(PROXY_ADMIN_PORT),
            'PROXY_PORT': str(PROXY_PORT),
            'MYSQL_PORT': str(MYSQL_PORT),
            'MYSQL_DATABASE': MYSQL_DATABASE,
            'MYSQL_USER': MYSQL_USER,
            'MYSQL_PASS': MYSQL_PASS,
        },
        conditions=[
            CheckDockerLogs('db', ["mysqld: ready for connections"], wait=5),
            CheckDockerLogs('proxysql', ["read_only_action RO=0 phase 3"], wait=5),
            WaitFor(init_mysql, wait=2),
            WaitFor(init_proxy, wait=2),
        ],
    ):
        yield BASIC_INSTANCE


def init_mysql():
    pymysql.connect(host=DOCKER_HOST, port=MYSQL_PORT, user=MYSQL_USER, passwd=MYSQL_PASS)


def init_proxy():
    pymysql.connect(host=DOCKER_HOST, port=PROXY_PORT, user=MYSQL_USER, passwd=MYSQL_PASS)
