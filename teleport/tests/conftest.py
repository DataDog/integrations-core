# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from .common import INSTANCE, USE_TELEPORT_CADDY

HOST = get_docker_hostname()

URL = "http://{}".format(HOST)


@pytest.fixture(scope="session")
def dd_environment():
    if USE_TELEPORT_CADDY:
        compose_file = os.path.join(get_here(), "docker", "caddy", "docker-compose.yaml")
        conditions = [
            CheckEndpoints(URL + ":3000/healthz", attempts=120),
        ]
        with docker_run(compose_file, conditions=conditions, sleep=5):
            yield INSTANCE
    else:
        compose_file = os.path.join(get_here(), "docker", "teleport", "docker-compose.yaml")
        with docker_run(
            compose_file,
            sleep=5,
            conditions=[
                CheckDockerLogs(identifier="teleport-service", patterns=["Starting Teleport"]),
                CheckEndpoints(URL + ":3000/healthz", attempts=120),
            ],
        ):
            yield {"teleport_url": URL, "diag_port": "3000"}


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture
def metrics_path():
    return os.path.join(get_here(), "fixtures", "metrics.txt")
