# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
from copy import deepcopy

from datadog_checks.dev import docker_run
from datadog_checks.cacti import CactiCheck

from .common import (
    HERE,
    HOST,
    INSTANCE_INTEGRATION
)


@pytest.fixture(scope="session")
def dd_environment():
    env = {'HOST': HOST}
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        env_vars=env,
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return CactiCheck('mapreduce', {}, {})


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
