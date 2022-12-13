# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest
from semver import VersionInfo

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE, KAFKA_VERSION


@pytest.fixture(scope='session')
def dd_environment():
    if VersionInfo.parse(KAFKA_VERSION) >= VersionInfo(major=3):
        compose_filename = "docker-compose.yml"
    else:
        compose_filename = "docker-compose-v2.yml"

    compose_file = os.path.join(HERE, 'compose', compose_filename)

    with docker_run(
        compose_file, conditions=[CheckDockerLogs(compose_file, [r'\[KafkaServer id=\d+\] started'], matches="all")]
    ):
        yield load_jmx_config(), {'use_jmx': True}
