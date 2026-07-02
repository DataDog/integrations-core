# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import docker_run
from datadog_checks.hdfs_namenode import HDFSNameNode

from .common import (
    FIXTURE_DIR,
    HERE,
    INSTANCE_INTEGRATION,
    NAME_SYSTEM_METADATA_URL,
    NAME_SYSTEM_STATE_URL,
    NAME_SYSTEM_URL,
)


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        log_patterns='Got finalize command for block pool',
        sleep=30,
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def instance():
    return INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return lambda instance: HDFSNameNode('hdfs_datanode', {}, [instance])


@pytest.fixture
def mocked_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


@pytest.fixture
def mocked_auth_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


def requests_get_mock(url, *args, **kwargs):
    if url == NAME_SYSTEM_STATE_URL:
        return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_namesystem_state.json'))
    elif url == NAME_SYSTEM_URL:
        return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_namesystem.json'))
    elif url == NAME_SYSTEM_METADATA_URL:
        return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_namesystem_info.json'))
