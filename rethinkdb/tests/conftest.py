# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Iterator

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.rethinkdb.types import Instance

from .cluster import setup_cluster
from .common import AGENT_PASSWORD, AGENT_USER, COMPOSE_ENV_VARS, COMPOSE_FILE, HOST, SERVER_PORTS


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    return {
        'host': HOST,
        'port': SERVER_PORTS['server0'],
        'user': AGENT_USER,
        'password': AGENT_PASSWORD,
    }


@pytest.fixture(scope='session')
def dd_environment(instance):
    # type: (Instance) -> Iterator
    conditions = [setup_cluster]

    log_patterns = [
        r'Server ready, "server0".*',
        r'Connected to server "server1".*',
        r'Connected to server "server2".*',
        r'Connected to proxy.*',
    ]

    with docker_run(COMPOSE_FILE, conditions=conditions, env_vars=COMPOSE_ENV_VARS, log_patterns=log_patterns):
        config = {'instances': [instance]}
        yield config
