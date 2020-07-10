# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run, get_here

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    env = {
        "ROOT_PASSWORD": common.INSTANCE_INTEGRATION.get("password", "1234"),
        "SSH_SERVER_IMAGE": common.SSH_SERVER_IMAGE,
    }

    with docker_run(
        compose_file=os.path.join(get_here(), "compose", "docker-compose.yml"),
        env_vars=env,
        log_patterns="Server listening on 0.0.0.0 port 22.",
    ):
        yield common.INSTANCE_INTEGRATION


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE_INTEGRATION)
