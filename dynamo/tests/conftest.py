# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from unittest import mock

import pytest

from datadog_checks.base.stubs import datadog_agent
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import COMPOSE_FILE, MOCKED_FRONTEND_INSTANCE, MOCKED_WORKER_INSTANCE


@pytest.fixture(autouse=True)
def gpu_monitoring_enabled():
    # Dynamo only runs when the Agent's GPU monitoring SKU is enabled; default it on for tests
    # that aren't specifically exercising that gating behavior. Patching the one key on the stub's
    # config dict leaves every other option answering normally.
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': True}):
        yield


E2E_METADATA = {
    'env_vars': {'DD_GPU_ENABLED': 'true'},
}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(MOCKED_FRONTEND_INSTANCE['openmetrics_endpoint']),
        CheckEndpoints(MOCKED_WORKER_INSTANCE['openmetrics_endpoint']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield (
            {'instances': [MOCKED_FRONTEND_INSTANCE, MOCKED_WORKER_INSTANCE]},
            E2E_METADATA,
        )


@pytest.fixture
def frontend_instance():
    return copy.deepcopy(MOCKED_FRONTEND_INSTANCE)


@pytest.fixture
def worker_instance():
    return copy.deepcopy(MOCKED_WORKER_INSTANCE)
