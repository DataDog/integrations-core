# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.utils import load_jmx_config

from .common import HERE


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yml')
    
    with docker_run(
        compose_file,
        conditions=[CheckDockerLogs(compose_file, [r'\[KafkaServer id=\d+\] started'], matches="all")]
    ):
        yield load_jmx_config(), {'use_jmx': True}
