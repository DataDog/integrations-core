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


@pytest.fixture
def mocked_request(fake_http_response):
    for url, fixture in (
        (DATANODE_INFO_URL, 'hdfs_datanode_info_jmx.json'),
        (DATANODE_BEANS_URL, 'hdfs_datanode_jmx.json'),
    ):
        with open(os.path.join(FIXTURE_DIR, fixture)) as f:
            fake_http_response(url, json_data=json.load(f))
