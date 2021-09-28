# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest
from mock import patch

from datadog_checks.dev import docker_run
from datadog_checks.dev.http import MockResponse
from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import FIXTURE_DIR, HERE, INSTANCE_INTEGRATION, TEST_PASSWORD, TEST_USERNAME


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


def requests_get_mock(*args, **kwargs):
    return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_datanode_jmx.json'))


def requests_metadata_mock(*args, **kwargs):
    return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_datanode_info_jmx.json'))


def requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return requests_get_mock(*args, **kwargs)
