# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock
import pymysql
import pytest

from datadog_checks.dev import TempDir, docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from datadog_checks.proxysql import ProxysqlCheck

from .common import (
    ALL_METRICS,
    BASIC_INSTANCE,
    BASIC_INSTANCE_TLS,
    DOCKER_HOST,
    INSTANCE_ALL_METRICS,
    INSTANCE_ALL_METRICS_STATS,
    MYSQL_DATABASE,
    MYSQL_PASS,
    MYSQL_PORT,
    MYSQL_USER,
    PROXY_ADMIN_PORT,
    PROXY_PORT,
    PROXYSQL_VERSION,
)


@pytest.fixture
def instance_basic():
    return deepcopy(BASIC_INSTANCE)


@pytest.fixture
def instance_basic_tls():
    return deepcopy(BASIC_INSTANCE_TLS)


@pytest.fixture()
def instance_all_metrics(instance_basic):
    return deepcopy(INSTANCE_ALL_METRICS)


@pytest.fixture()
def instance_stats_user(instance_basic):
    return deepcopy(INSTANCE_ALL_METRICS_STATS)


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'compose', 'docker-compose.yml')

    with TempDir('proxysql-data') as tmp_dir:
        with docker_run(
            compose_file,
            env_vars={
                'PROXY_ADMIN_PORT': str(PROXY_ADMIN_PORT),
                'PROXY_PORT': str(PROXY_PORT),
                'MYSQL_PORT': str(MYSQL_PORT),
                'MYSQL_DATABASE': MYSQL_DATABASE,
                'MYSQL_USER': MYSQL_USER,
                'MYSQL_PASS': MYSQL_PASS,
                'TMP_DATA_DIR': tmp_dir,
            },
            conditions=[
                CheckDockerLogs(
                    'db',
                    ["MySQL init process done. Ready for start up."],
                    wait=5,
                ),
                CheckDockerLogs('proxysql', ["read_only_action RO=0 phase 3"], wait=5),
                WaitFor(init_mysql, wait=2),
                WaitFor(init_proxy, wait=2),
            ],
            attempts=2,
        ):
            instance = deepcopy(INSTANCE_ALL_METRICS)
            cert_src = os.path.join(tmp_dir, 'proxysql-ca.pem')
            cert_dest = "/etc/ssl/certs/proxysql-ca.pem"
            if PROXYSQL_VERSION.startswith('2'):
                # SSL is only available with version 2.x of ProxySQL
                instance['tls_verify'] = True
                instance['tls_ca_cert'] = cert_dest
                instance['validate_hostname'] = False
            yield instance, {'docker_volumes': ['{}:{}'.format(cert_src, cert_dest)]}


def init_mysql():
    pymysql.connect(host=DOCKER_HOST, port=MYSQL_PORT, user=MYSQL_USER, passwd=MYSQL_PASS)


def init_proxy():
    pymysql.connect(host=DOCKER_HOST, port=PROXY_PORT, user=MYSQL_USER, passwd=MYSQL_PASS)


def get_check(instance):
    """Simple helper method to get a check instance from a config instance."""
    return ProxysqlCheck('proxysql', {}, [instance])


def _assert_all_metrics(aggregator):
    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def _assert_metadata(datadog_agent, check_id=''):
    raw_version = PROXYSQL_VERSION
    major, minor = raw_version.split('.')[:2]
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': mock.ANY,
        'version.raw': mock.ANY,
    }
    datadog_agent.assert_metadata(check_id, version_metadata)
