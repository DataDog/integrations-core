# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.base.utils.http_testing import http_client_session  # noqa: F401
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import (
    CONFIG,
    GITLAB_LOCAL_MASTER_PORT,
    GITLAB_LOCAL_RUNNER_PORT,
    GITLAB_MASTER_URL,
    GITLAB_RUNNER_URL,
    GITLAB_TEST_TOKEN,
    HERE,
    HOST,
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

    conditions = [
        CheckDockerLogs(compose_file, patterns='Gitlab is up!', wait=5),
        CheckDockerLogs(compose_file, patterns='Configuration loaded', wait=5),
        CheckDockerLogs(compose_file, patterns='Metrics server listening', wait=5),
    ]

    for _ in range(2):
        conditions.extend(
            [
                CheckEndpoints(GITLAB_RUNNER_URL, attempts=180, wait=3),
                CheckEndpoints('{}/ci'.format(GITLAB_MASTER_URL), attempts=90, wait=3),
            ]
        )

    with docker_run(
        compose_file=compose_file,
        env_vars=env,
        conditions=conditions,
    ):
        yield CONFIG, E2E_METADATA


def _mocked_requests_get(*args, **kwargs):
    url = args[0]

    if url == 'http://{}:{}/metrics'.format(HOST, GITLAB_LOCAL_RUNNER_PORT):
        fixtures_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
        with open(fixtures_path, 'r') as f:
            text_data = f.read()
            return mock.MagicMock(
                status_code=200,
                iter_lines=lambda **kwargs: text_data.split("\n"),
                headers={'Content-Type': "text/plain"},
            )
    elif url == 'http://{}:{}/ci'.format(HOST, GITLAB_LOCAL_MASTER_PORT):
        return mock.MagicMock(status_code=200)

    return mock.MagicMock(status_code=404)


@pytest.fixture()
def mock_data():
    with mock.patch(
        'requests.Session.get',
        side_effect=_mocked_requests_get,
    ):
        yield
