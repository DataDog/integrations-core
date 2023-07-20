# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Iterator  # noqa: F401

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.rethinkdb.types import Instance  # noqa: F401

from .cluster import setup_cluster
from .common import (
    AGENT_PASSWORD,
    AGENT_USER,
    BOOTSTRAP_SERVER,
    COMPOSE_ENV_VARS,
    COMPOSE_FILE,
    HOST,
    SERVER_PORTS,
    SERVERS,
    TAGS,
)


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    return {
        'host': HOST,
        'port': SERVER_PORTS['server0'],
        'username': AGENT_USER,
        'password': AGENT_PASSWORD,
        'tags': TAGS,
    }


@pytest.fixture(scope='session')
def dd_environment(instance):
    # type: (Instance) -> Iterator
    log_patterns = [r'Server ready, "{}".*'.format(BOOTSTRAP_SERVER), r'Connected to proxy.*']
    log_patterns.extend(r'Connected to server "{}".*'.format(server) for server in SERVERS - {BOOTSTRAP_SERVER})
    wait_servers_ready = CheckDockerLogs(COMPOSE_FILE, patterns=log_patterns, matches='all')

    conditions = [wait_servers_ready, setup_cluster]

    with docker_run(COMPOSE_FILE, conditions=conditions, env_vars=COMPOSE_ENV_VARS, mount_logs=True):
        yield instance
