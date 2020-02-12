# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, Dict, Iterator

import pytest

from datadog_checks.dev import docker_run

from .common import CONTAINER_NAME, HERE, IMAGE, PORT, SERVER_NAME


@pytest.fixture(scope='session')
def dd_environment():
    # type: () -> Iterator[dict]
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    env_vars = {
        'RETHINKDB_PORT': str(PORT),
        'RETHINKDB_IMAGE': IMAGE,
        'RETHINKDB_CONTAINER_NAME': CONTAINER_NAME,
        'RETHINKDB_SERVER_NAME': SERVER_NAME,
    }

    with docker_run(compose_file, env_vars=env_vars, log_patterns=[r'Server ready.*']):
        instance = {}  # type: Dict[str, Any]
        config = {'instances': [instance]}
        yield config
