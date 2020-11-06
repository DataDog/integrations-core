# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.voltdb._types import Instance

from . import common


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    conditions = [
        CheckDockerLogs(compose_file, patterns=['Server completed initialization']),
    ]
    env_vars = {
        'VOLTDB_API_PORT': str(common.VOLTDB_API_PORT),
    }
    with docker_run(compose_file, conditions=conditions, env_vars=env_vars):
        yield instance


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    return {
        'host': common.HOST,
        'port': common.VOLTDB_API_PORT,
        'username': 'doggo',
        'password': 'doggopass',  # SHA256: e81255cee7bd2c4fbb4c8d6e9d6ba1d33a912bdfa9901dc9acfb2bd7f3e8eeb1
    }
