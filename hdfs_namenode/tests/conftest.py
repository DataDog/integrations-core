# (C) Datadog, Inc. 2018-2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest
from mock import patch

from datadog_checks.dev import docker_run
from datadog_checks.hdfs_namenode import HDFSNameNode

from .common import (
    HERE,
    INSTANCE_INTEGRATION,
    NAME_SYSTEM_METADATA_URL,
    NAME_SYSTEM_STATE_URL,
    NAME_SYSTEM_URL,
    TEST_PASSWORD,
    TEST_USERNAME,
)


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        log_patterns='Got finalize command for block pool',
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def instance():
    return INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return lambda instance: HDFSNameNode('hdfs_datanode', {}, [instance])


@pytest.fixture
def mocked_request():
    with patch("requests.get", new=requests_get_mock):
        yield


@pytest.fixture
def mocked_auth_request():
    with patch("requests.get", new=requests_auth_mock):
        yield


def requests_get_mock(url, *args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if url == NAME_SYSTEM_STATE_URL:
        system_state_file_path = os.path.join(HERE, 'fixtures', 'hdfs_namesystem_state.json')
        with open(system_state_file_path, 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif url == NAME_SYSTEM_URL:
        system_file_path = os.path.join(HERE, 'fixtures', 'hdfs_namesystem.json')
        with open(system_file_path, 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif url == NAME_SYSTEM_METADATA_URL:
        system_file_path = os.path.join(HERE, 'fixtures', 'hdfs_namesystem_info.json')
        with open(system_file_path, 'r') as f:
            body = f.read()
            return MockResponse(body, 200)


def requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return requests_get_mock(*args, **kwargs)
