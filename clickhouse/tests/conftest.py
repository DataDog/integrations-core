# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import clickhouse_driver
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints, WaitFor

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    config = get_instance_config()

    conditions = []
    for i in range(common.CLICKHOUSE_NODE_NUM):
        conditions.append(
            CheckDockerLogs(
                identifier='clickhouse-0{}'.format(i + 1),
                patterns='Logging errors to /var/log/clickhouse-server/clickhouse-server.err.log',
                wait=5,
            )
        )
        conditions.append(
            CheckEndpoints(endpoints=['http://{}:{}'.format(common.HOST, common.HTTP_START_PORT + i)], wait=5),
        )
        conditions.append(
            WaitFor(
                func=ping_clickhouse(common.HOST, common.TCP_START_PORT + i, config['username'], config['password']),
                wait=5,
            )
        )

    with docker_run(common.COMPOSE_FILE, conditions=conditions, sleep=10, attempts=2, mount_logs=True):
        yield config


@pytest.fixture
def instance():
    return get_instance_config()


def ping_clickhouse(host, port, username, password):
    def _ping_clickhouse():
        client = clickhouse_driver.Client(
            host=host,
            port=port,
            user=username,
            password=password,
        )
        client.connection.connect()
        client.connection.ping()
        return True

    return _ping_clickhouse


def get_instance_config() -> dict:
    return deepcopy(common.CONFIG)


@pytest.fixture
def clickhouse_client(instance):
    return clickhouse_driver.Client(
        host=instance['server'],
        port=instance['port'],
        user=instance['username'],
        password=instance['password'],
    )
