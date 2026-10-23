# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient
from datadog_checks.dev import docker_run, get_docker_hostname, get_e2e_discovery_metadata, get_here
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
            yield {"teleport_url": URL, "diag_port": "3000"}, get_e2e_discovery_metadata()


@pytest.fixture
def instance():
    return INSTANCE.copy()


@pytest.fixture
def metrics_path():
    return os.path.join(get_here(), "fixtures", "metrics.txt")


@pytest.fixture
def mock_metrics(
    fake_http: FakeHTTPClient, fake_http_response: Callable, instance: dict, metrics_path: str
) -> Iterator[None]:
    diag_addr = f"{instance['teleport_url']}:{instance['diag_port']}"
    fake_http_response(f'{diag_addr}/healthz')
    fake_http_response(f'{diag_addr}/metrics', Path(metrics_path).read_bytes())
    yield
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [
        ('GET', f'{diag_addr}/healthz'),
        ('GET', f'{diag_addr}/metrics'),
    ]
