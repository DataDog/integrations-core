# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.mapreduce import MapReduceCheck

from .common import (
    CLUSTER_INFO_URL,
    HERE,
    HOST,
    INSTANCE_INTEGRATION,
    MOCKED_E2E_HOSTS,
    MR_JOB_COUNTERS_URL,
    MR_JOBS_URL,
    MR_TASKS_URL,
    YARN_APPS_URL_BASE,
    setup_mapreduce,
)


@pytest.fixture(scope="session")
def dd_environment():
    env = {'HOSTNAME': HOST}
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        conditions=[WaitFor(setup_mapreduce, attempts=5, wait=5)],
        env_vars=env,
    ):
        # 'custom_hosts' in metadata provides native /etc/hosts mappings in the agent's docker container
        yield INSTANCE_INTEGRATION, {'custom_hosts': get_custom_hosts()}


@pytest.fixture
def check():
    return lambda instance: MapReduceCheck('mapreduce', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


@pytest.fixture
def mocked_auth_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


def get_custom_hosts():
    return [(host, '127.0.0.1') for host in MOCKED_E2E_HOSTS]


def requests_get_mock(url, *args, **kwargs):
    if url.startswith(YARN_APPS_URL_BASE):
        query = url[len(YARN_APPS_URL_BASE) :]
        if query in ["?states=RUNNING&applicationTypes=MAPREDUCE", "?applicationTypes=MAPREDUCE&states=RUNNING"]:
            return MockHTTPResponse(file_path=os.path.join(HERE, "fixtures", "apps_metrics"))
        else:
            raise Exception(
                "Apps URL must have the two query parameters: states=RUNNING and applicationTypes=MAPREDUCE"
            )

    if url == MR_JOBS_URL:
        return MockHTTPResponse(file_path=os.path.join(HERE, "fixtures", "job_metrics"))

    if url == MR_JOB_COUNTERS_URL:
        return MockHTTPResponse(file_path=os.path.join(HERE, "fixtures", "job_counter_metrics"))

    if url == MR_TASKS_URL:
        return MockHTTPResponse(file_path=os.path.join(HERE, "fixtures", "task_metrics"))

    if url == CLUSTER_INFO_URL:
        return MockHTTPResponse(file_path=os.path.join(HERE, "fixtures", "cluster_info"))

    raise Exception("There is no mock request for {}".format(url))
