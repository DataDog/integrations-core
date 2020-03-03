# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from time import sleep

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import (
    CONFIG,
    GITLAB_LOCAL_PORT,
    GITLAB_LOCAL_PROMETHEUS_PORT,
    GITLAB_PROMETHEUS_ENDPOINT,
    GITLAB_TEST_PASSWORD,
    GITLAB_URL,
    HERE,
    PROMETHEUS_ENDPOINT,
)


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up and initialize gitlab
    """

    # specify couchbase container name
    env = {
        'GITLAB_TEST_PASSWORD': GITLAB_TEST_PASSWORD,
        'GITLAB_LOCAL_PORT': str(GITLAB_LOCAL_PORT),
        'GITLAB_LOCAL_PROMETHEUS_PORT': str(GITLAB_LOCAL_PROMETHEUS_PORT),
    }

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yml'),
        env_vars=env,
        conditions=[
            CheckEndpoints(GITLAB_URL, attempts=200),
            CheckEndpoints(GITLAB_PROMETHEUS_ENDPOINT),
        ],
    ):
        # run pre-test commands
        for _ in range(100):
            requests.get(GITLAB_URL)
        sleep(2)

        yield CONFIG
