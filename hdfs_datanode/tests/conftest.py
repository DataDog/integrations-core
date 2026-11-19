# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import DATANODE_BEANS_URL, DATANODE_INFO_URL, FIXTURE_DIR, HERE, INSTANCE_INTEGRATION


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


def _register_fixture(fake_http_response, url, fixture_name):
    with open(os.path.join(FIXTURE_DIR, fixture_name)) as f:
        fake_http_response(url, json_data=json.load(f))


@pytest.fixture
def mocked_request(fake_http_response):
    for url in (DATANODE_BEANS_URL, DATANODE_INFO_URL):
        _register_fixture(fake_http_response, url, 'hdfs_datanode_jmx.json')


@pytest.fixture
def mocked_metadata_request(fake_http_response):
    _register_fixture(fake_http_response, DATANODE_INFO_URL, 'hdfs_datanode_info_jmx.json')
