# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from unittest import mock

import pytest

from datadog_checks.base.stubs import datadog_agent
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import COMPOSE_FILE, MOCKED_INSTANCE


@pytest.fixture(autouse=True)
def gpu_monitoring_enabled():
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': True}):
        yield


E2E_METADATA = {'env_vars': {'DD_GPU_ENABLED': 'true'}}


@pytest.fixture(scope='session')
def dd_environment():
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(MOCKED_INSTANCE['openmetrics_endpoint']),
    ]
    with docker_run(COMPOSE_FILE, conditions=conditions):
        yield ({'instances': [MOCKED_INSTANCE]}, E2E_METADATA)


@pytest.fixture
def instance():
    return copy.deepcopy(MOCKED_INSTANCE)
