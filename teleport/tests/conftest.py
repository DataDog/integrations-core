# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs

from .common import INSTANCE, USE_TELEPORT_CADDY


@pytest.fixture(scope="session")
def dd_environment():
    if USE_TELEPORT_CADDY:
        compose_file = os.path.join(get_here(), "docker", "caddy", "docker-compose.yaml")
        conditions = [
            CheckDockerLogs(identifier="teleport-service", patterns=["server running"]),
        ]
        with docker_run(compose_file, conditions=conditions):
            instance = {"teleport_url": "http://127.0.0.1", "diag_port": "3001"}
            yield instance
    else:
        compose_file = os.path.join(get_here(), "docker", "teleport", "docker-compose.yaml")
        with docker_run(compose_file, sleep=5):
            yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture
def metrics_path():
    return os.path.join(get_here(), "fixtures", "metrics.txt")
