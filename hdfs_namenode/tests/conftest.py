# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from json import loads
from pathlib import Path

import pytest

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
def mocked_request(fake_http_response):
    fixtures = {
        NAME_SYSTEM_STATE_URL: 'hdfs_namesystem_state.json',
        NAME_SYSTEM_URL: 'hdfs_namesystem.json',
        NAME_SYSTEM_METADATA_URL: 'hdfs_namesystem_info.json',
    }
    for url, fixture_name in fixtures.items():
        fake_http_response(url, json_data=loads((Path(FIXTURE_DIR) / fixture_name).read_text()))
