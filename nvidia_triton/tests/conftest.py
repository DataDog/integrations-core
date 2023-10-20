# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import pytest
from . import common

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(common.INSTANCE_DISABLED_SERVER_INFO["openmetrics_endpoint"]),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.INSTANCE_DISABLED_SERVER_INFO],
        }


@pytest.fixture
def instance():
    return copy.deepcopy(common.INSTANCE)

@pytest.fixture
def instance_metrics():
    return copy.deepcopy(common.INSTANCE_DISABLED_SERVER_INFO)

