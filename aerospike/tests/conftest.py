# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev.docker import CheckDockerLogs, docker_run

from .common import COMPOSE_FILE, HERE, OPENMETRICS_V2_INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        COMPOSE_FILE,
        env_vars={'AEROSPIKE_CONFIG': os.path.join(HERE, 'docker/config')},
        conditions=[CheckDockerLogs(COMPOSE_FILE, ['service ready: soon there will be cake!'])],
        attempts=2,
    ):
        yield OPENMETRICS_V2_INSTANCE


@pytest.fixture
def instance_openmetrics_v2():
    return deepcopy(OPENMETRICS_V2_INSTANCE)
