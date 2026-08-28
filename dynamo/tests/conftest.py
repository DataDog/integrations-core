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
    # that aren't specifically exercising that gating behavior.
    real_get_config = datadog_agent.get_config

    def fake_get_config(option):
        return 'true' if option == 'gpu.enabled' else real_get_config(option)

    with mock.patch('datadog_checks.dynamo.check.datadog_agent.get_config', side_effect=fake_get_config):
        yield


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(MOCKED_FRONTEND_INSTANCE['openmetrics_endpoint']),
        CheckEndpoints(MOCKED_WORKER_INSTANCE['openmetrics_endpoint']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [MOCKED_FRONTEND_INSTANCE, MOCKED_WORKER_INSTANCE],
        }


@pytest.fixture
def frontend_instance():
    return copy.deepcopy(MOCKED_FRONTEND_INSTANCE)


@pytest.fixture
def worker_instance():
    return copy.deepcopy(MOCKED_WORKER_INSTANCE)
