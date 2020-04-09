# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import subprocess
from copy import deepcopy

import pytest
import requests
from mock import patch

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.mapreduce import MapReduceCheck

from .common import (
    CLUSTER_INFO_URL,
    CONTAINER_NAME,
    HERE,
    HOST,
    INSTANCE_INTEGRATION,
    MR_JOB_COUNTERS_URL,
    MR_JOBS_URL,
    MR_TASKS_URL,
    TEST_PASSWORD,
    TEST_USERNAME,
    YARN_APPS_URL_BASE,
)


@pytest.fixture(scope="session")
def dd_environment():
    env = {'HOSTNAME': HOST}
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        conditions=[WaitFor(setup_mapreduce, attempts=240, wait=5)],
        env_vars=env,
    ):
        yield INSTANCE_INTEGRATION


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


def setup_mapreduce():
    # Run a job in order to get metrics from the environment
    subprocess.Popen(
        [
            'docker',
            'exec',
            CONTAINER_NAME,
            '/usr/local/hadoop/bin/yarn',
            'jar',
            '/usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-2.7.1.jar',
            'grep',
            'input',
            'output',
            '\'dfs[a-z.]+\'',
        ],
        close_fds=True,
    )

    # Called in WaitFor which catches exceptions
    r = requests.get("{}/ws/v1/cluster/apps?states=RUNNING".format(INSTANCE_INTEGRATION['resourcemanager_uri']))

    return r.json().get("apps", None) is not None


def requests_get_mock(*args, **kwargs):
    url = args[0]
    # The parameter that creates the query params (kwargs) is an unordered dict,
    # so the query params can be in any order
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
