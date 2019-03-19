# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from time import sleep

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import (
    HERE, GITLAB_TEST_TOKEN, GITLAB_RUNNER_URL, GITLAB_LOCAL_RUNNER_PORT, GITLAB_LOCAL_MASTER_PORT, CONFIG
)


@pytest.fixture(scope="session", autouse=True)
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

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yml'),
        env_vars=env,
        conditions=[CheckEndpoints(GITLAB_RUNNER_URL, attempts=180)],
    ):
        # run pre-test commands
        for _ in range(100):
            requests.get(GITLAB_RUNNER_URL)
        sleep(2)

        yield CONFIG
