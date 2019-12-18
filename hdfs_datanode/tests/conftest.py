# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from copy import deepcopy

import pytest
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
    return lambda instance: HDFSDataNode('hdfs_datanode', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request():
    with patch('requests.get', new=requests_get_mock):
        yield


@pytest.fixture
def mocked_metadata_request():
    with patch('requests.get', new=requests_metadata_mock):
        yield


@pytest.fixture
def mocked_auth_request():
    with patch('requests.get', new=requests_auth_mock):
        yield


def _requests_mock(fixture, *args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    with open(fixture, 'r') as f:
        body = f.read()
        return MockResponse(body, 200)


def requests_get_mock(*args, **kwargs):
    fixture = os.path.join(HERE, 'fixtures', 'hdfs_datanode_jmx.json')
    return _requests_mock(fixture, *args, **kwargs)


def requests_metadata_mock(*args, **kwargs):
    fixture = os.path.join(HERE, 'fixtures', 'hdfs_datanode_info_jmx.json')
    return _requests_mock(fixture, *args, **kwargs)


def requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return requests_get_mock(*args, **kwargs)
