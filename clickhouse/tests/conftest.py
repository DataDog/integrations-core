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
    conditions = []

    for i in range(6):
        conditions.append(CheckEndpoints(['http://{}:{}'.format(common.HOST, common.HTTP_START_PORT + i)]))
        conditions.append(
            CheckDockerLogs(
                'clickhouse-0{}'.format(i + 1), 'Logging errors to /var/log/clickhouse-server/clickhouse-server.err.log'
            )
        )

    conditions.append(
        WaitFor(
            ping_clickhouse(
                common.CONFIG['server'],
                common.CONFIG['port'],
                common.CONFIG['username'],
                common.CONFIG['password'],
            )
        )
    )

    with docker_run(common.COMPOSE_FILE, conditions=conditions, sleep=10, attempts=2):
        yield common.CONFIG


@pytest.fixture
def instance():
    return deepcopy(common.CONFIG)


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
