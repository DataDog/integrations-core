# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import docker_run
from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import FIXTURE_DIR, HERE, INSTANCE_INTEGRATION


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        log_patterns='Got finalize command for block pool',
        sleep=30,
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return lambda instance: HDFSDataNode('hdfs_datanode', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


@pytest.fixture
def mocked_metadata_request(mock_http):
    mock_http.get.side_effect = requests_metadata_mock
    yield


@pytest.fixture
def mocked_auth_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


def requests_get_mock(url, *args, **kwargs):
    return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_datanode_jmx.json'))


def requests_metadata_mock(url, *args, **kwargs):
    return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'hdfs_datanode_info_jmx.json'))
