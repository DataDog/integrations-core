# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        log_patterns=[r'datanode:\(\d+\) is available', 'Starting Hive Metastore Server', 'Starting HiveServer2'],
        sleep=2,
    ):
        yield load_jmx_config(), {'use_jmx': True}
