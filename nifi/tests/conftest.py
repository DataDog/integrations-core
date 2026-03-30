# ABOUTME: Pytest fixtures for NiFi integration tests.
# ABOUTME: Provides dd_environment for Docker-based tests and instance fixtures.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


def setup_test_flows():
    """Run the setup-flow.sh script to create test processors and connections."""
    script = os.path.join(common.HERE, 'docker', 'setup-flow.sh')
    run_command(
        ['bash', script],
        check=True,
        env={
            **os.environ,
            'NIFI_API_URL': common.NIFI_API_URL,
            'NIFI_USERNAME': common.NIFI_USERNAME,
            'NIFI_PASSWORD': common.NIFI_PASSWORD,
        },
    )


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        conditions=[
            CheckDockerLogs('nifi', ['Started Application Controller'], attempts=120, wait=5),
            WaitFor(setup_test_flows, attempts=30, wait=5),
        ],
    ):
        yield common.CHECK_CONFIG


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)
