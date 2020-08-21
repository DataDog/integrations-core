# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from copy import deepcopy

import pytest
from datadog_test_libs.utils.mock_dns import mock_local
from mock import patch

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
    TEST_PASSWORD,
    TEST_USERNAME,
    YARN_APPS_URL_BASE,
    setup_mapreduce,
)

MOCKED_HOSTS = ('namenode', 'datanode', 'resourcemanager', 'nodemanager', 'historyserver')


@pytest.fixture(scope="session")
def dd_environment(mock_local_mapreduce_dns):
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
def mocked_request():
    with patch("requests.get", new=requests_get_mock):
        yield


@pytest.fixture
def mocked_auth_request():
    with patch("requests.get", new=requests_auth_mock):
        yield


@pytest.fixture(scope='session')
def mock_local_mapreduce_dns():
    mapping = {x: ('127.0.0.1', 443) for x in MOCKED_HOSTS}
    with mock_local(mapping):
        yield


def get_custom_hosts():
    # creat a mapping of mapreduce hostnames to localhost for DNS resolution
    custom_hosts = [(host, '127.0.0.1') for host in MOCKED_E2E_HOSTS]
    return custom_hosts


def requests_get_mock(*args, **kwargs):
    url = args[0]
    # The parameter that creates the query params (kwargs) is an unordered dict,
    #   so the query params can be in any order
    if url.startswith(YARN_APPS_URL_BASE):
        query = url[len(YARN_APPS_URL_BASE) :]
        if query in ["?states=RUNNING&applicationTypes=MAPREDUCE", "?applicationTypes=MAPREDUCE&states=RUNNING"]:
            return _mock_response(os.path.join(HERE, "fixtures", "apps_metrics"))
        else:
            raise Exception(
                "Apps URL must have the two query parameters: states=RUNNING and applicationTypes=MAPREDUCE"
            )

    elif url == MR_JOBS_URL:
        return _mock_response(os.path.join(HERE, "fixtures", "job_metrics"))

    elif url == MR_JOB_COUNTERS_URL:
        return _mock_response(os.path.join(HERE, "fixtures", "job_counter_metrics"))

    elif url == MR_TASKS_URL:
        return _mock_response(os.path.join(HERE, "fixtures", "task_metrics"))

    elif url == CLUSTER_INFO_URL:
        return _mock_response(os.path.join(HERE, "fixtures", "cluster_info"))

    else:
        raise Exception("There is no mock request for {}".format(url))


def _mock_response(filepath):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    with open(filepath, "r") as f:
        body = f.read()
        return MockResponse(body, 200)


def requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return requests_get_mock(*args, **kwargs)
