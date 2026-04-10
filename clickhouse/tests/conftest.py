# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import clickhouse_connect
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints, WaitFor

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    config = get_instance_config()

    conditions = [
        CheckDockerLogs(
            identifier='clickhouse',
            patterns='Logging errors to /var/log/clickhouse-server/clickhouse-server.err.log',
            wait=5,
        ),
        CheckEndpoints(endpoints=['http://{}:{}'.format(config['server'], config['port'])], wait=5),
        WaitFor(
            func=ping_clickhouse(config['server'], config['port'], config['username'], config['password']),
            wait=5,
        ),
    ]

    compose_file, mount_logs = common.get_compose_file()
    with docker_run(compose_file, conditions=conditions, sleep=10, attempts=2, mount_logs=mount_logs):
        yield config


@pytest.fixture
def instance():
    config = get_instance_config()
    if common.is_legacy(common.CLICKHOUSE_VERSION):
        config['use_advanced_queries'] = False
    else:
        config['use_legacy_queries'] = False

    return config


def ping_clickhouse(host, port, username, password):
    def _ping_clickhouse():
        client = get_clickhouse_client(
            host=host,
            port=port,
            username=username,
            password=password,
        )
        return client.ping()

    return _ping_clickhouse


def get_clickhouse_client(host, port, username, password):
    return clickhouse_connect.get_client(
        host=host,
        port=port,
        username=username,
        password=password,
    )


def get_instance_config() -> dict:
    return deepcopy(common.CONFIG)
