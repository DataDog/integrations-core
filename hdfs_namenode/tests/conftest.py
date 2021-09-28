# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from mock import patch

from datadog_checks.dev import docker_run
from datadog_checks.dev.http import MockResponse
from datadog_checks.hdfs_namenode import HDFSNameNode

from .common import (
    FIXTURE_DIR,
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
    if url == NAME_SYSTEM_STATE_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_namesystem_state.json'))
    elif url == NAME_SYSTEM_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_namesystem.json'))
    elif url == NAME_SYSTEM_METADATA_URL:
        return MockResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_namesystem_info.json'))


def requests_auth_mock(*args, **kwargs):
    # Make sure we're passing in authentication
    assert 'auth' in kwargs, "Error, missing authentication"

    # Make sure we've got the correct username and password
    assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password"

    # Return mocked request.get(...)
    return requests_get_mock(*args, **kwargs)
