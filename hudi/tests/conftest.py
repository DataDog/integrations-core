# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from .common import CHECK_CONFIG, HERE


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yaml')
    with docker_run(
        compose_file=compose_file,
        conditions=[CheckDockerLogs('spark-app-hudi', 'finished: show at script.scala:163')],
    ):
        yield CHECK_CONFIG, {'use_jmx': True}
