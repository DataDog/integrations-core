# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope='session')
def dd_environment(instance):
    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')

    conditions = [
        CheckDockerLogs(compose_file, 'Starting Azure IoT Edge Security Daemon', wait=5),
        CheckDockerLogs(compose_file, 'Successfully started module edgeAgent', wait=5),
        CheckDockerLogs(compose_file, r'[mgmt] .* 200 OK', wait=5),  # Verify any connectivity issues.
    ]

    env_vars = {
        "IOT_DEVICE_CONNSTR": common.IOT_DEVICE_CONNECTION_STRING,
        "IOT_PROMETHEUS_PORT": str(common.IOT_PROMETHEUS_PORT),
    }

    with docker_run(compose_file, conditions=conditions, env_vars=env_vars):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {}
