# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Iterator

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.rethinkdb._types import Instance

from .cluster import setup_cluster
from .common import AGENT_PASSWORD, AGENT_USER, COMPOSE_ENV_VARS, COMPOSE_FILE, HOST, SERVER_PORTS

E2E_METADATA = {'start_commands': ['pip install rethinkdb==2.4.4']}


@pytest.fixture(
    scope='session',
    params=[
        # By default, only the admin user has access to system tables (which this integration fetches metrics from).
        # We must make sure that users can setup the integration with either the admin user, or a specific user
        # set up for the sole purpose of the Agent.
        pytest.param((None, None), id='unauthenticated_admin'),
        pytest.param((AGENT_USER, AGENT_PASSWORD), id='authenticated'),
    ],
)
def instance(request):
    # type: (Any) -> Instance
    user, password = request.param
    return {
        'host': HOST,
        'port': SERVER_PORTS['server0'],
        'user': user,
        'password': password,
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
        yield config, E2E_METADATA
