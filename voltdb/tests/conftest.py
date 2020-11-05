# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.voltdb._types import Instance

from . import common


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    env_vars = {
        'VOLTDB_API_PORT': str(common.VOLTDB_API_PORT),
    }
    with docker_run(compose_file, env_vars=env_vars):
        yield instance


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    return {
        'hostname': common.HOST,
        'port': common.VOLTDB_API_PORT,
    }
