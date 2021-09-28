# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import (
    CONFIG,
    GITLAB_LOCAL_MASTER_PORT,
    GITLAB_LOCAL_RUNNER_PORT,
    GITLAB_RUNNER_URL,
    GITLAB_TEST_TOKEN,
    HERE,
)

# Needed to mount volume for logging
E2E_METADATA = {'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up and initialize gitlab_runner
    """

    # specify couchbase container name
    env = {
        'GITLAB_TEST_TOKEN': GITLAB_TEST_TOKEN,
        'GITLAB_LOCAL_MASTER_PORT': str(GITLAB_LOCAL_MASTER_PORT),
        'GITLAB_LOCAL_RUNNER_PORT': str(GITLAB_LOCAL_RUNNER_PORT),
    }
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yml')
    with docker_run(
        compose_file=compose_file,
        env_vars=env,
        conditions=[
            CheckDockerLogs(
                compose_file, ['Gitlab is up!', 'Configuration loaded', 'Metrics server listening'], wait=5
            ),
            CheckEndpoints(GITLAB_RUNNER_URL, attempts=180),
        ],
    ):
        yield CONFIG, E2E_METADATA
