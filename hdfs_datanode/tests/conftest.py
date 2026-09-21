# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy
from json import loads
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import DATANODE_URI, FIXTURE_DIR, HERE, INSTANCE_INTEGRATION


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
    metadata_url = f'{DATANODE_URI}jmx?qry={HDFSDataNode.HDFS_DATANODE_VERSION_NAME}'
    metrics_url = f'{DATANODE_URI}jmx?qry={HDFSDataNode.HDFS_DATANODE_BEAN_NAME}'
    metadata = loads((Path(FIXTURE_DIR) / 'hdfs_datanode_info_jmx.json').read_text())
    metrics = loads((Path(FIXTURE_DIR) / 'hdfs_datanode_jmx.json').read_text())
    fake_http_response(metadata_url, json_data=metadata)
    fake_http_response(metrics_url, json_data=metrics)
