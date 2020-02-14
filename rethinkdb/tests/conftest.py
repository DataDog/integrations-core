# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, Dict, Iterator, List

import pytest

from datadog_checks.dev import docker_run

from .common import CONNECT_SERVER_PORT, HERE, IMAGE, PROXY_PORT


@pytest.fixture(scope='session')
def dd_environment():
    # type: () -> Iterator[Dict[str, Any]]
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    env_vars = {
        'RETHINKDB_IMAGE': IMAGE,
        'RETHINKDB_CONNECT_SERVER_PORT': str(CONNECT_SERVER_PORT),
        'RETHINKDB_PROXY_PORT': str(PROXY_PORT),
    }  # type: Dict[str, str]

    log_patterns = [
        r'Server ready, "server0".*',
        r'Connected to server "server1".*',
        r'Connected to server "server2".*',
        r'Connected to proxy.*',
    ]  # type: List[str]

    with docker_run(compose_file, env_vars=env_vars, log_patterns=log_patterns):
        instance = {}  # type: Dict[str, Any]
        config = {'instances': [instance]}
        yield config
