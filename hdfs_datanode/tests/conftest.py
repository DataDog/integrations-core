# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest
from copy import deepcopy
from mock import patch

from datadog_checks.dev import docker_run
from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import HERE, INSTANCE_INTEGRATION, TEST_PASSWORD, TEST_USERNAME


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        log_patterns='Got finalize command for block pool',
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return HDFSDataNode('hdfs_datanode')


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request():
    with patch('requests.get', new=requests_get_mock):
        yield


@pytest.fixture
def mocked_auth_request():
    with patch('requests.get', new=requests_auth_mock):
        yield


def requests_get_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    datanode_beans_file_path = os.path.join(HERE, 'fixtures', 'hdfs_datanode_jmx')
    with open(datanode_beans_file_path, 'r') as f:
        body = f.read()
        return MockResponse(body, 200)


def requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return requests_get_mock(*args, **kwargs)
